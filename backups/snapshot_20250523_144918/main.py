import sys
from PyQt5.QtWidgets import QApplication
from app.gui import MainWindow
from app.agent import Agent

def main():
    agent = Agent()
    app = QApplication(sys.argv)
    window = MainWindow(agent)
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
