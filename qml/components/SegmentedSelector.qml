import QtQuick
import QtQuick.Controls.Basic

// Row of mutually exclusive options. ``options``: [{label, value}].
Row {
    id: root

    property var options: []
    property var value
    signal activated(var value)

    spacing: 0

    Repeater {
        model: root.options
        Button {
            id: option
            readonly property bool selected: modelData.value === root.value
            objectName: "option_" + modelData.value
            implicitHeight: 34
            implicitWidth: Math.max(64, label.implicitWidth + 24)
            hoverEnabled: true
            checkable: false
            onClicked: {
                root.value = modelData.value
                root.activated(modelData.value)
            }

            contentItem: Text {
                id: label
                text: modelData.label
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.family: Theme.fontBody
                font.pixelSize: Theme.fontSizeBody - 1
                font.bold: option.selected
                color: option.selected ? Theme.background : (option.hovered ? Theme.goldBright : Theme.textSecondary)
            }
            background: Rectangle {
                color: option.selected ? Theme.gold : (option.hovered ? Theme.backgroundRaised : Theme.panel)
                border.width: 1
                border.color: option.selected ? Theme.goldBright : Theme.panelBorder
                radius: 0
                Behavior on color { ColorAnimation { duration: Theme.durationFast } }
            }
        }
    }
}
