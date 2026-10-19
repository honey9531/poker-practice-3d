import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Transport controls for stepping through a recorded hand.
Rectangle {
    id: root

    property var replay: null  // the Replay bridge

    color: Theme.backgroundRaised

    Rectangle {
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: 1
        color: Theme.divider
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.spacingLarge
        anchors.rightMargin: Theme.spacingLarge
        spacing: Theme.spacing
        enabled: root.replay !== null

        ActionButton {
            objectName: "replayBack"
            text: "‹ Back"
            enabled: root.replay && root.replay.position > 0
            onClicked: root.replay.stepBack()
        }
        ActionButton {
            objectName: "replayPlay"
            variant: "primary"
            text: root.replay && root.replay.playing ? "Pause" : "Play"
            onClicked: root.replay.togglePlay()
        }
        ActionButton {
            objectName: "replayForward"
            text: "Next ›"
            enabled: root.replay && root.replay.position < root.replay.steps - 1
            onClicked: root.replay.stepForward()
        }

        Slider {
            id: slider
            objectName: "replaySlider"
            Layout.fillWidth: true
            from: 0
            to: Math.max(1, root.replay ? root.replay.steps - 1 : 1)
            stepSize: 1
            snapMode: Slider.SnapAlways
            value: root.replay ? root.replay.position : 0
            onMoved: root.replay.seek(Math.round(value))

            background: Rectangle {
                x: slider.leftPadding
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: slider.availableWidth
                height: 4
                radius: 2
                color: Theme.panelBorder
                Rectangle {
                    width: slider.visualPosition * parent.width
                    height: parent.height
                    radius: 2
                    color: Theme.gold
                }
            }
            handle: Rectangle {
                x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width)
                y: slider.topPadding + slider.availableHeight / 2 - height / 2
                width: 18
                height: 18
                radius: 9
                color: Theme.textPrimary
                border.color: Theme.goldDim
            }
        }

        Text {
            objectName: "replayStep"
            text: root.replay ? (root.replay.position + 1) + " / " + root.replay.steps : ""
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeBody
            color: Theme.textSecondary
        }

        SegmentedSelector {
            objectName: "revealSelector"
            options: [{ label: "As played", value: false }, { label: "Show all cards", value: true }]
            value: root.replay ? root.replay.revealAll : false
            onActivated: v => root.replay.revealAll = v
        }
    }
}
