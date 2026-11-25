"""Demostración en consola del asistente médico virtual con Gemini.

Requiere GEMINI_API_KEY en el archivo .env. Ejecutar: python -m app.demo_chat
"""

from app.ai.asistente import AsistenteMedico
from app.ai.proveedores import ErrorProveedor, ProveedorGemini


def main() -> None:
    """Abre una conversación en la terminal hasta que el usuario escriba "salir"."""
    print("=" * 70)
    print("ASISTENTE MÉDICO VIRTUAL - demostración en consola (escribe 'salir' para terminar)")
    print("Aviso: herramienta orientativa. No sustituye una consulta médica.")
    print("=" * 70)
    try:
        proveedor = ProveedorGemini()
    except ErrorProveedor as error:
        print(f"No se pudo iniciar el asistente: {error}")
        return
    print(f"Modelo: {proveedor.nombre_modelo}\n")

    asistente = AsistenteMedico(proveedor)
    while True:
        texto = input("Tú: ").strip()
        if texto.lower() in ("salir", "exit", "quit"):
            break
        if not texto:
            continue
        try:
            respuesta = asistente.enviar(texto)
        except ErrorProveedor as error:
            print(f"[Error] {error}\n")
            continue
        etiqueta = " [URGENCIA]" if respuesta.urgencia else (" [DERIVAR AL MÉDICO]" if respuesta.derivar else "")
        print(f"\nAsistente{etiqueta}: {respuesta.texto}\n")


if __name__ == "__main__":
    main()
