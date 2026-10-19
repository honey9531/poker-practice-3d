import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Modal confirmation in the table's style.
Popup {
    id: root

    property string title
    property string text
    property string confirmText: "Confirm"
    property string cancelText: "Cancel"

    signal confirmed()

    anchors.centerIn: Overlay.overlay
    width: Math.min(440, (parent ? parent.width : 440) - 48)
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

        Text {
            text: root.title
            font.family: Theme.fontDisplay
            font.pixelSize: Theme.fontSizeLarge + 2
            color: Theme.textPrimary
        }
        Text {
            Layout.fillWidth: true
            text: root.text
            wrapMode: Text.WordWrap
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeBody
            color: Theme.textSecondary
        }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            Layout.topMargin: Theme.spacing
            spacing: Theme.spacing
            ActionButton {
                objectName: "dialogCancel"
                text: root.cancelText
                onClicked: root.close()
            }
            ActionButton {
                objectName: "dialogConfirm"
                text: root.confirmText
                variant: "primary"
                onClicked: {
                    root.close()
                    root.confirmed()
                }
            }
        }
    }
}
