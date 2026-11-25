"""Asistente médico virtual: une el filtro de seguridad, el system prompt, el proveedor LLM y la base de datos."""

import sqlite3
from dataclasses import dataclass

from app.ai import seguridad
from app.ai.prompts import SYSTEM_PROMPT, contexto_triaje
from app.ai.proveedores import Mensaje, ProveedorLLM
from app.core.modelos import ResultadoTriaje
from app.db import repositorio


@dataclass
class RespuestaAsistente:
    """Lo que la interfaz necesita para mostrar un turno del chat."""

    texto: str
    derivar: bool          # True si se activó el umbral de duda o hubo un signo de alarma.
    urgencia: bool         # True si fue un signo de alarma (respuesta fija, sin consultar al modelo).
    signos: list[str]      # Signos de alarma detectados en el mensaje del usuario.


class AsistenteMedico:
    """Mantiene una conversación, aplica las reglas de seguridad y guarda cada mensaje si hay base de datos."""

    def __init__(
        self,
        proveedor: ProveedorLLM,
        conexion: sqlite3.Connection | None = None,
        consulta_id: int | None = None,
        triaje: ResultadoTriaje | None = None,
    ):
        """Prepara el asistente; si se pasa el resultado del triaje, se añade como contexto."""
        self.proveedor = proveedor
        self.conexion = conexion
        self.consulta_id = consulta_id
        self.historial: list[Mensaje] = []
        self.derivado = False  # Una vez derivado, la interfaz mantiene visible el aviso y el mapa.
        self.instrucciones = SYSTEM_PROMPT
        if triaje is not None:
            self.instrucciones += "\n\n" + contexto_triaje(
                triaje.dictamen_final, triaje.prolog.fase, triaje.r.probabilidad, triaje.motivos
            )

    def _guardar(self, rol: str, contenido: str, umbral_duda: bool = False, modelo: str | None = None) -> None:
        """Guarda el mensaje en la base solo si el asistente tiene conexión y consulta asociadas."""
        if self.conexion is not None and self.consulta_id is not None:
            repositorio.guardar_mensaje(self.conexion, self.consulta_id, rol, contenido, umbral_duda, modelo)

    def enviar(self, texto_usuario: str) -> RespuestaAsistente:
        """Procesa un mensaje del usuario y devuelve la respuesta revisada del asistente."""
        self.historial.append(Mensaje("usuario", texto_usuario))
        self._guardar("usuario", texto_usuario)

        # 1. Filtro previo: ante un signo de alarma no se consulta al modelo y se deriva de inmediato.
        signos = seguridad.detectar_alarmas(texto_usuario)
        if signos:
            texto = seguridad.MENSAJE_URGENCIA.format(signos=", ".join(s.replace("_", " ") for s in signos))
            self.derivado = True
            self.historial.append(Mensaje("asistente", texto))
            self._guardar("asistente", texto, umbral_duda=True, modelo="filtro_seguridad")
            return RespuestaAsistente(texto=texto, derivar=True, urgencia=True, signos=signos)

        # 2. Se consulta al modelo con todo el historial.
        texto_modelo = self.proveedor.responder(self.instrucciones, self.historial)

        # 3. Filtro posterior: se detecta la marca de duda que el modelo debe escribir.
        revisada = seguridad.revisar_respuesta(texto_modelo)
        self.derivado = self.derivado or revisada.derivar
        self.historial.append(Mensaje("asistente", revisada.texto))
        self._guardar("asistente", revisada.texto, umbral_duda=revisada.derivar, modelo=getattr(self.proveedor, "modelo_usado", self.proveedor.nombre_modelo))
        return RespuestaAsistente(texto=revisada.texto, derivar=revisada.derivar, urgencia=False, signos=[])
