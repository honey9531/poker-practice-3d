import QtQuick

// Dealer button ("D") or blind marker ("SB" / "BB") as a small puck.
Item {
    id: root

    property string kind: "D"  // "D", "SB" or "BB"
    property real size: 26

    readonly property bool dealer: kind === "D"

    width: size
    height: size

    Rectangle {
        anchors.fill: parent
        anchors.topMargin: root.size * 0.08
        anchors.bottomMargin: -root.size * 0.08
        radius: width / 2
        color: "#000000"
        opacity: 0.35
    }
    Rectangle {
        anchors.fill: parent
        radius: width / 2
        antialiasing: true
        border.width: Math.max(1, root.size * 0.06)
        border.color: root.dealer ? "#b9b2a2" : Qt.darker(color, 1.4)
        color: root.dealer ? "#f6f2e8" : (root.kind === "SB" ? "#3d6ea8" : "#c99a3a")
        gradient: root.dealer ? dealerGradient : null

        Gradient {
            id: dealerGradient
            GradientStop { position: 0.0; color: "#ffffff" }
            GradientStop { position: 1.0; color: "#ddd6c6" }
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.74
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: root.dealer ? "#cfc7b6" : Qt.rgba(1, 1, 1, 0.4)
        }

        Text {
            anchors.centerIn: parent
            text: root.kind
            font.family: root.dealer ? Theme.fontDisplay : Theme.fontBody
            font.bold: true
            font.pixelSize: root.size * (root.dealer ? 0.5 : 0.36)
            color: root.dealer ? "#1d1b18" : "#ffffff"
        }
    }
}
