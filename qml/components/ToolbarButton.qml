import QtQuick
import QtQuick.Controls.Basic

// Compact text button for the top bar.
Button {
    id: control

    implicitHeight: 32
    leftPadding: 14
    rightPadding: 14
    hoverEnabled: true

    contentItem: Text {
        text: control.text
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody - 1
        color: control.hovered ? Theme.goldBright : Theme.textSecondary
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: control.enabled ? 1.0 : 0.4
    }

    background: Rectangle {
        radius: Theme.radius - 2
        color: control.down ? Theme.panel : (control.hovered ? Theme.backgroundRaised : "transparent")
        border.width: control.visualFocus ? 1 : 0
        border.color: Theme.gold
    }
}
