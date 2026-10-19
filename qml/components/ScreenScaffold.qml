import QtQuick
import QtQuick.Layouts

// Common frame for secondary screens: top bar with back navigation and a title.
Rectangle {
    id: root

    property string title
    default property alias content: contentArea.data

    signal backRequested()

    color: Theme.background

    Rectangle {
        id: topBar
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: Theme.topBarHeight
        color: Theme.backgroundRaised

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: Theme.spacing
            anchors.rightMargin: Theme.spacing
            spacing: Theme.spacing

            ToolbarButton {
                objectName: "backButton"
                text: "‹  Menu"
                onClicked: root.backRequested()
            }

            Text {
                Layout.fillWidth: true
                text: root.title
                font.family: Theme.fontDisplay
                font.pixelSize: Theme.fontSizeLarge
                color: Theme.textPrimary
                elide: Text.ElideRight
            }
        }

        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: 1
            color: Theme.divider
        }
    }

    Item {
        id: contentArea
        anchors {
            left: parent.left; right: parent.right
            top: topBar.bottom; bottom: parent.bottom
        }
    }
}
