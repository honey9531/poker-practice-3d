import QtQuick
import QtQuick.Controls.Basic

// Betting action button. ``variant``: "fold", "neutral", "primary" or "allin".
Button {
    id: control

    property string variant: "neutral"
    property string shortcutHint: ""

    readonly property color baseColor: variant === "primary" ? Theme.gold
                                     : variant === "fold" ? "#3a2522"
                                     : variant === "allin" ? "#7c2a22"
                                     : "#2b3a31"
    readonly property color labelColor: variant === "primary" ? Theme.background : Theme.textPrimary

    implicitWidth: Math.max(112, contentItem.implicitWidth + 28)
    implicitHeight: 42
    hoverEnabled: true

    contentItem: Item {
        implicitWidth: labels.implicitWidth
        implicitHeight: labels.implicitHeight

        Column {
            id: labels
            anchors.centerIn: parent
            spacing: 0
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: control.text
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody
                font.bold: true
                color: control.labelColor
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: control.shortcutHint !== ""
                text: control.shortcutHint
                font.family: Theme.fontBody
                font.pixelSize: 10
                color: control.labelColor
                opacity: 0.55
            }
        }
    }

    background: Rectangle {
        radius: Theme.radius
        color: control.down ? Qt.darker(control.baseColor, 1.25)
             : control.hovered ? Qt.lighter(control.baseColor, 1.15)
             : control.baseColor
        border.width: 1
        border.color: control.visualFocus ? Theme.goldBright : Qt.lighter(control.baseColor, 1.35)
        opacity: control.enabled ? 1 : 0.35
        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
    }
}
