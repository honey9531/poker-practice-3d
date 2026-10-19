import QtQuick
import QtQuick.Controls.Basic

// Wide, understated button used on the main menu.
Button {
    id: control

    property bool primary: false

    implicitWidth: 280
    implicitHeight: 46
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus

    contentItem: Text {
        text: control.text
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeLarge - 2
        font.letterSpacing: 1.2
        color: control.primary ? Theme.background
                               : (control.hovered ? Theme.goldBright : Theme.textPrimary)
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        opacity: control.enabled ? 1.0 : 0.4
    }

    background: Rectangle {
        radius: Theme.radius
        color: control.primary
               ? (control.down ? Theme.goldDim : (control.hovered ? Theme.goldBright : Theme.gold))
               : (control.down ? Theme.panel : (control.hovered ? Theme.backgroundRaised : "transparent"))
        border.width: 1
        border.color: control.primary ? Theme.goldBright
                                      : (control.hovered || control.visualFocus ? Theme.gold : Theme.panelBorder)
        Behavior on color { ColorAnimation { duration: Theme.durationFast } }
    }
}
