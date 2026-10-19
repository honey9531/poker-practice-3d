import QtQuick
import QtQuick.Effects
import QtQuick.Window

// A playing card. The card body always keeps poker proportions (63 x 88)
// and is centred in whatever box the parent gives it.
Item {
    id: root

    // "As", "Td", ... ; empty means an unknown card, which always shows its back.
    property string card: ""
    property bool faceUp: true
    property bool highlighted: false
    property bool dimmed: false
    property bool animated: true

    readonly property real aspect: 88 / 63
    readonly property bool showingFace: card !== "" && faceUp
    readonly property real cornerRadius: body.width * 34 / 630

    implicitWidth: 72
    implicitHeight: implicitWidth * aspect

    // Slide in from (dx, dy), relative to the card's final position.
    function dealFrom(dx, dy, delay) {
        dealAnimation.stop()
        offset.x = dx
        offset.y = dy
        body.opacity = 0
        dealAnimation.pauseDuration = delay || 0
        if (!animated) {
            offset.x = 0
            offset.y = 0
            body.opacity = 1
            return
        }
        dealAnimation.start()
    }

    transform: Translate { id: offset }

    SequentialAnimation {
        id: dealAnimation
        property alias pauseDuration: pause.duration
        PauseAnimation { id: pause }
        PropertyAction { target: body; property: "opacity"; value: 1 }
        ParallelAnimation {
            NumberAnimation { target: offset; property: "x"; to: 0; duration: 380; easing.type: Easing.OutCubic }
            NumberAnimation { target: offset; property: "y"; to: 0; duration: 380; easing.type: Easing.OutCubic }
        }
    }

    Item {
        id: body
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(root.width, root.height / root.aspect)
        height: width * root.aspect
        y: (root.height - height) / 2 - (root.highlighted ? height * 0.07 : 0)
        Behavior on y {
            enabled: root.animated
            NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic }
        }

        // Soft drop shadow.
        Rectangle {
            id: shadowSource
            anchors.fill: parent
            radius: root.cornerRadius
            color: "black"
            visible: false
        }
        MultiEffect {
            source: shadowSource
            anchors.fill: shadowSource
            anchors.topMargin: body.height * 0.02
            anchors.bottomMargin: -body.height * 0.02
            blurEnabled: true
            blur: 0.6
            blurMax: 16
            autoPaddingEnabled: true
            opacity: root.highlighted ? 0.55 : 0.35
        }

        Flipable {
            id: flipable
            anchors.fill: parent

            front: Image {
                objectName: "cardFront"
                anchors.fill: parent
                source: root.card !== "" ? Qt.resolvedUrl("../../assets/cards/" + root.card + ".svg") : ""
                sourceSize: Qt.size(Math.ceil(width * Screen.devicePixelRatio), Math.ceil(height * Screen.devicePixelRatio))
                smooth: true
                visible: root.card !== ""
            }
            back: Image {
                objectName: "cardBack"
                anchors.fill: parent
                source: Qt.resolvedUrl("../../assets/cards/back.svg")
                sourceSize: Qt.size(Math.ceil(width * Screen.devicePixelRatio), Math.ceil(height * Screen.devicePixelRatio))
                smooth: true
            }

            transform: Rotation {
                origin.x: flipable.width / 2
                origin.y: flipable.height / 2
                axis { x: 0; y: 1; z: 0 }
                angle: root.showingFace ? 0 : 180
                Behavior on angle {
                    enabled: root.animated
                    NumberAnimation { duration: 340; easing.type: Easing.InOutQuad }
                }
            }
        }

        Rectangle {
            objectName: "dimOverlay"
            anchors.fill: parent
            radius: root.cornerRadius
            color: "#0b0b0b"
            opacity: root.dimmed ? 0.5 : 0
            Behavior on opacity { enabled: root.animated; NumberAnimation { duration: Theme.durationNormal } }
        }

        Rectangle {
            objectName: "highlightRing"
            anchors.fill: parent
            anchors.margins: -Math.max(2, body.width * 0.03)
            radius: root.cornerRadius + Math.max(2, body.width * 0.03)
            color: "transparent"
            border.color: Theme.goldBright
            border.width: Math.max(2, body.width * 0.035)
            opacity: root.highlighted ? 1 : 0
            Behavior on opacity { enabled: root.animated; NumberAnimation { duration: Theme.durationNormal } }
        }
    }
}
