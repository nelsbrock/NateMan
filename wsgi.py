"""
WSGI-Schnittstelle. Startet NateMan.
von Niklas Elsbrock
"""

from nateman import create_app


if __name__ == "__main__":
    create_app().run()
else:
    app = create_app()
