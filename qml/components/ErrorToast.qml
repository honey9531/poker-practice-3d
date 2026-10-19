import QtQuick

// Brief, non-blocking message for recoverable problems.
Rectangle {
    id: root

    property string text: ""

    function show(message) {
        text = message
        animation.restart()
    }

    width: Math.min(label.implicitWidth + 32, (parent ? parent.width : 800) - 48)
    height: label.implicitHeight + 14
    radius: height / 2
    color: "#e0301a17"
    border.color: Theme.accentRed
    opacity: 0
    visible: opacity > 0

    Text {
        id: label
        anchors.centerIn: parent
        width: Math.min(implicitWidth, root.width - 24)
        elide: Text.ElideRight
        text: root.text
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeBody
        color: Theme.textPrimary
    }

    SequentialAnimation {
        id: animation
        NumberAnimation { target: root; property: "opacity"; to: 1; duration: Theme.durationFast }
        PauseAnimation { duration: 3200 }
        NumberAnimation { target: root; property: "opacity"; to: 0; duration: 400 }
    }
}
