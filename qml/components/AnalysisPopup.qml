import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Opponents' decisions in the last hand, with their reasoning and cards.
// Only populated by the bridge after the hand is over.
Popup {
    id: root

    property var entries: []  // [{name, street, action, reason, cards}]

    anchors.centerIn: Overlay.overlay
    width: Math.min(720, (parent ? parent.width : 720) - 48)
    height: Math.min(520, (parent ? parent.height : 520) - 48)
    modal: true
    focus: true
    padding: Theme.spacingLarge
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    Overlay.modal: Rectangle { color: "#a0000000" }

    background: Rectangle {
        radius: Theme.radius * 2
        color: Theme.panel
        border.width: 1
        border.color: Theme.goldDim
    }

    contentItem: ColumnLayout {
        spacing: Theme.spacing

        RowLayout {
            Layout.fillWidth: true
            Text {
                Layout.fillWidth: true
                text: "Hand analysis"
                font.family: Theme.fontDisplay
                font.pixelSize: Theme.fontSizeLarge + 2
                color: Theme.textPrimary
            }
            ToolbarButton { text: "Close"; onClicked: root.close() }
        }

        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "How each opponent reasoned. Equity is the estimated chance of winning against random hands."
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeSmall
            color: Theme.textMuted
        }

        ListView {
            objectName: "analysisList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 6
            model: root.entries
            ScrollBar.vertical: ScrollBar {}

            delegate: Rectangle {
                width: ListView.view.width
                height: row.implicitHeight + 12
                radius: Theme.radius
                color: index % 2 ? "transparent" : "#14ffffff"

                RowLayout {
                    id: row
                    anchors.fill: parent
                    anchors.margins: 6
                    spacing: Theme.spacing

                    Row {
                        spacing: 2
                        Repeater {
                            model: modelData.cards
                            PlayingCard { width: 30; height: width * aspect; card: modelData; animated: false }
                        }
                    }
                    Text {
                        Layout.preferredWidth: 80
                        text: modelData.name
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.fontSizeBody
                        font.bold: true
                        color: Theme.textPrimary
                    }
                    Text {
                        Layout.preferredWidth: 64
                        text: modelData.street.charAt(0).toUpperCase() + modelData.street.slice(1)
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.fontSizeSmall
                        color: Theme.textMuted
                    }
                    Text {
                        Layout.preferredWidth: 120
                        text: modelData.action
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.fontSizeBody
                        color: Theme.actionColor(modelData.action)
                    }
                    Text {
                        Layout.fillWidth: true
                        text: modelData.reason
                        wrapMode: Text.WordWrap
                        font.family: Theme.fontBody
                        font.pixelSize: Theme.fontSizeSmall
                        color: Theme.textSecondary
                    }
                }
            }
        }
    }
}
