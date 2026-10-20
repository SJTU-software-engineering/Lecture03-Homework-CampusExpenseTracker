import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QMessageBox


@pytest.fixture(scope="session")
def app():
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    return application


@pytest.fixture
def dialogs(monkeypatch):
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, message: messages.append(message))
    return messages
