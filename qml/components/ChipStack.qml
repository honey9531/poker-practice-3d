import QtQuick

// A stack of identical chips seen at an angle. Only the top chip draws its
// full face; chips below draw just their visible edge band with inserts.
Item {
    id: root

    property int count: 1
    property color baseColor: "#b3252d"
    property color insertColor: "#f1ece2"
    property color textColor: "#7a161c"
    property string label: ""
    property real chipWidth: 40

    readonly property real tilt: 0.42  // apparent height / width of the top face
    readonly property real faceHeight: chipWidth * tilt
    readonly property real thickness: Math.max(2, chipWidth * 0.1)
    readonly property color sideColor: Qt.darker(baseColor, 1.18)
    readonly property color seamColor: Qt.darker(baseColor, 1.4)
    readonly property color edgeInsert: Qt.tint(insertColor, Qt.rgba(baseColor.r, baseColor.g, baseColor.b, 0.25))

    implicitWidth: chipWidth
    implicitHeight: faceHeight + count * thickness
    width: chipWidth
    height: implicitHeight

    Repeater {
        model: root.count

        // Chip ``index`` (0 = bottom). Its top face sits at ``faceTop``.
        Item {
            id: chip
            readonly property real faceTop: (root.count - 1 - index) * root.thickness
            readonly property real jitter: ((index * 37) % 5 - 2) * root.chipWidth * 0.008
            x: jitter
            y: faceTop
            width: root.chipWidth
            height: root.faceHeight + root.thickness
            z: index

            // Lower ellipse (bottom edge), with a dark seam under it.
            Item {
                y: root.thickness + 0.6
                width: parent.width
                height: root.faceHeight
                Rectangle {
                    width: parent.width; height: parent.width; radius: width / 2
                    color: root.seamColor
                    antialiasing: true
                    transform: Scale { yScale: root.tilt }
                }
            }
            Item {
                y: root.thickness
                width: parent.width
                height: root.faceHeight
                Rectangle {
                    width: parent.width; height: parent.width; radius: width / 2
                    color: root.sideColor
                    antialiasing: true
                    transform: Scale { yScale: root.tilt }
                }
            }
            // Straight band joining the two ellipses.
            Rectangle {
                y: root.faceHeight / 2
                width: parent.width
                height: root.thickness
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Qt.darker(root.sideColor, 1.35) }
                    GradientStop { position: 0.35; color: Qt.lighter(root.sideColor, 1.08) }
                    GradientStop { position: 1.0; color: Qt.darker(root.sideColor, 1.45) }
                }
            }
            // Edge inserts on the visible front half, alternating between chips.
            Repeater {
                model: [-60, 0, 60].map(a => a + ((index % 3) - 1) * 20)
                Rectangle {
                    readonly property real angle: modelData * Math.PI / 180
                    readonly property real visibleWidth: root.chipWidth * 0.12 * Math.cos(angle)
                    visible: Math.abs(modelData) < 85
                    x: root.chipWidth / 2 + (root.chipWidth / 2) * Math.sin(angle) - visibleWidth / 2
                    y: root.faceHeight / 2 * (1 + Math.cos(angle)) + 0.5
                    width: Math.max(0, visibleWidth)
                    height: root.thickness - 1
                    color: root.edgeInsert
                }
            }
            // Upper ellipse (top face), hidden under the next chip except at the top.
            Item {
                width: parent.width
                height: root.faceHeight
                visible: index < root.count - 1
                Rectangle {
                    width: parent.width; height: parent.width; radius: width / 2
                    color: root.baseColor
                    antialiasing: true
                    transform: Scale { yScale: root.tilt }
                }
            }
        }
    }

    // Top chip face.
    Item {
        x: root.count > 0 ? ((root.count - 1) * 37 % 5 - 2) * root.chipWidth * 0.008 : 0
        width: root.chipWidth
        height: root.faceHeight
        z: root.count
        visible: root.count > 0
        PokerChip {
            width: root.chipWidth
            baseColor: root.baseColor
            insertColor: root.insertColor
            textColor: root.textColor
            label: root.label
            transform: Scale { yScale: root.tilt }
        }
    }
}
