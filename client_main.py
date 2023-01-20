import client
import sys
from PyQt5.QtWidgets import *

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = client.Login()
    client.show()
    sys.exit(app.exec())
