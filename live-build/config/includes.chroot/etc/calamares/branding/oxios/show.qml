import QtQuick 2.0
import QtQuick.Controls 2.0

Item {
    id: root
    property string distroName: "Oxi OS"
    property string version: "development"

    Image {
        id: background
        anchors.fill: parent
        source: "logo.png"
        fillMode: Image.PreserveAspectFit
        opacity: 0.1
    }

    Column {
        anchors.centerIn: parent
        spacing: 20

        Image {
            source: "logo.png"
            width: 200
            height: 200
            fillMode: Image.PreserveAspectFit
            smooth: true
        }

        Text {
            text: root.distroName + " " + root.version
            font.pixelSize: 28
            font.bold: true
            color: "#18a999"
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            text: "Fast • Minimal • Stable\nA modern Linux distribution focused on simplicity, performance and reliability."
            font.pixelSize: 16
            color: "#ffffff"
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }

    Timer {
        interval: 30000
        running: true
        repeat: true
        onTriggered: {
            // Keep alive
        }
    }
}
