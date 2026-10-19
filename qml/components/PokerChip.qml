import QtQuick
import QtQuick.Shapes

// A single casino chip seen from above.
Item {
    id: root

    property color baseColor: "#b3252d"
    property color insertColor: "#f1ece2"
    property color textColor: "#7a161c"
    property string label: ""

    readonly property real r: width / 2
    readonly property real rimWidth: r * 0.2
    readonly property int insertCount: 6

    implicitWidth: 48
    implicitHeight: width

    // Body.
    Rectangle {
        anchors.fill: parent
        radius: root.r
        color: root.baseColor
        border.width: Math.max(1, root.r * 0.03)
        border.color: Qt.darker(root.baseColor, 1.45)
        antialiasing: true
    }

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        // Alternating edge inserts: one dashed stroke around the rim.
        ShapePath {
            id: rimPath
            readonly property real radius: root.r - root.rimWidth / 2 - root.r * 0.03
            strokeColor: root.insertColor
            strokeWidth: root.rimWidth
            fillColor: "transparent"
            capStyle: ShapePath.FlatCap
            strokeStyle: ShapePath.DashLine
            // Dash and gap of equal length; units are stroke widths.
            dashPattern: {
                const unit = (2 * Math.PI * radius) / (2 * root.insertCount * strokeWidth)
                return [unit, unit]
            }
            PathAngleArc {
                centerX: root.r; centerY: root.r
                radiusX: rimPath.radius; radiusY: rimPath.radius
                startAngle: -90 + 360 / (4 * root.insertCount)
                sweepAngle: 360
            }
        }

        // Fine dashed inner ring.
        ShapePath {
            id: ringPath
            readonly property real radius: root.r * 0.66
            strokeColor: root.insertColor
            strokeWidth: Math.max(1, root.r * 0.045)
            fillColor: "transparent"
            capStyle: ShapePath.FlatCap
            strokeStyle: ShapePath.DashLine
            dashPattern: {
                const unit = (2 * Math.PI * radius) / (2 * 18 * strokeWidth)
                return [unit, unit]
            }
            PathAngleArc {
                centerX: root.r; centerY: root.r
                radiusX: ringPath.radius; radiusY: ringPath.radius
                startAngle: 0
                sweepAngle: 360
            }
        }
    }

    // Centre inlay with the denomination.
    Rectangle {
        anchors.centerIn: parent
        width: root.r * 1.12
        height: width
        radius: width / 2
        color: "#f4efe4"
        border.width: Math.max(1, root.r * 0.05)
        border.color: Qt.darker(root.baseColor, 1.15)
        antialiasing: true

        Text {
            readonly property real size: root.r * (root.label.length >= 3 ? 0.36 : 0.46)
            anchors.centerIn: parent
            // Below a legible size the colour alone identifies the chip.
            visible: size >= 7 && root.label !== ""
            text: root.label
            color: root.textColor
            font.family: Theme.fontBody
            font.bold: true
            font.pixelSize: Math.max(7, size)
        }
    }

    // Lighting: light from above, darker towards the bottom.
    Rectangle {
        anchors.fill: parent
        radius: root.r
        antialiasing: true
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.22) }
            GradientStop { position: 0.45; color: Qt.rgba(1, 1, 1, 0.0) }
            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.22) }
        }
    }
}
