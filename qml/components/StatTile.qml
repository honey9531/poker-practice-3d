import QtQuick
import QtQuick.Layouts

// One statistic: a large value with a label and an optional detail line.
Rectangle {
    id: root

    property string label
    property string value
    property string detail: ""
    property color valueColor: Theme.textPrimary

    implicitWidth: 200
    implicitHeight: 104
    radius: Theme.radius * 1.5
    color: Theme.panel
    border.width: 1
    border.color: Theme.panelBorder

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.spacing + 4
        spacing: 2

        Text {
            text: root.label.toUpperCase()
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeSmall - 1
            font.letterSpacing: 1.2
            color: Theme.textMuted
        }
        Text {
            objectName: "statValue"
            text: root.value
            font.family: Theme.fontDisplay
            font.pixelSize: 30
            color: root.valueColor
        }
        Text {
            Layout.fillWidth: true
            visible: root.detail !== ""
            text: root.detail
            elide: Text.ElideRight
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeSmall
            color: Theme.textSecondary
        }
        Item { Layout.fillHeight: true }
    }
}
