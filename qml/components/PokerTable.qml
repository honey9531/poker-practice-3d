import QtQuick
import QtQuick.Effects
import QtQuick.Shapes

// The table surface: padded rail, wood trim, textured felt with soft lighting
// and a betting line. Purely decorative; content is laid out by the parent.
Item {
    id: root

    readonly property real railWidth: Math.max(14, height * 0.085)
    readonly property real trimWidth: Math.max(2, height * 0.012)
    // Felt rectangle in the table's coordinates (useful for placing content).
    readonly property rect feltRect: Qt.rect(railWidth, railWidth, width - 2 * railWidth, height - 2 * railWidth)

    // SVG path of a stadium (rectangle with fully rounded ends).
    function stadium(x, y, w, h) {
        const r = h / 2
        return "M " + (x + r) + " " + y
            + " L " + (x + w - r) + " " + y
            + " A " + r + " " + r + " 0 0 1 " + (x + w - r) + " " + (y + h)
            + " L " + (x + r) + " " + (y + h)
            + " A " + r + " " + r + " 0 0 1 " + (x + r) + " " + y + " Z"
    }

    // Shadow cast on the floor.
    Rectangle {
        id: shadowShape
        anchors.fill: parent
        radius: height / 2
        color: "black"
        visible: false
    }
    MultiEffect {
        source: shadowShape
        anchors.fill: shadowShape
        anchors.topMargin: root.height * 0.04
        anchors.bottomMargin: -root.height * 0.04
        blurEnabled: true
        blur: 1.0
        blurMax: 48
        autoPaddingEnabled: true
        opacity: 0.6
    }

    // Padded leather rail.
    Rectangle {
        anchors.fill: parent
        radius: height / 2
        border.width: 1
        border.color: Theme.railEdge
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#3b322c" }
            GradientStop { position: 0.08; color: "#2a231f" }
            GradientStop { position: 0.5; color: "#1a1613" }
            GradientStop { position: 0.92; color: "#110e0c" }
            GradientStop { position: 1.0; color: "#0b0908" }
        }
    }

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        // Highlight along the top of the padding.
        ShapePath {
            strokeColor: Qt.rgba(1, 1, 1, 0.07)
            strokeWidth: Math.max(1, root.railWidth * 0.22)
            fillColor: "transparent"
            PathSvg {
                path: root.stadium(root.railWidth * 0.35, root.railWidth * 0.35,
                                   root.width - root.railWidth * 0.7, root.height - root.railWidth * 0.7)
            }
        }
        // Stitching.
        ShapePath {
            strokeColor: Qt.rgba(0.85, 0.75, 0.55, 0.22)
            strokeWidth: 1
            fillColor: "transparent"
            strokeStyle: ShapePath.DashLine
            dashPattern: [4, 4]
            PathSvg {
                path: root.stadium(root.railWidth * 0.18, root.railWidth * 0.18,
                                   root.width - root.railWidth * 0.36, root.height - root.railWidth * 0.36)
            }
        }
        // Wood trim between rail and felt.
        ShapePath {
            strokeColor: "#5a3d24"
            strokeWidth: root.trimWidth * 2
            fillColor: "#0a3824"
            PathSvg {
                path: root.stadium(root.railWidth - root.trimWidth, root.railWidth - root.trimWidth,
                                   root.width - 2 * (root.railWidth - root.trimWidth),
                                   root.height - 2 * (root.railWidth - root.trimWidth))
            }
        }
        // Felt with a soft overhead light.
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.width / 2
                centerY: root.height * 0.42
                focalX: centerX
                focalY: centerY
                centerRadius: root.width * 0.55
                GradientStop { position: 0.0; color: "#1a6a45" }
                GradientStop { position: 0.45; color: Theme.felt }
                GradientStop { position: 1.0; color: "#08301e" }
            }
            PathSvg { path: root.stadium(root.feltRect.x, root.feltRect.y, root.feltRect.width, root.feltRect.height) }
        }
        // Inner shadow under the trim.
        ShapePath {
            strokeColor: Qt.rgba(0, 0, 0, 0.35)
            strokeWidth: Math.max(2, root.railWidth * 0.3)
            fillColor: "transparent"
            PathSvg { path: root.stadium(root.feltRect.x, root.feltRect.y, root.feltRect.width, root.feltRect.height) }
        }
        // Betting line.
        ShapePath {
            readonly property real inset: root.feltRect.height * 0.15
            strokeColor: Qt.rgba(0.9, 0.85, 0.7, 0.16)
            strokeWidth: Math.max(1, root.height * 0.004)
            fillColor: "transparent"
            PathSvg {
                path: root.stadium(root.feltRect.x + root.feltRect.height * 0.15, root.feltRect.y + root.feltRect.height * 0.15,
                                   root.feltRect.width - root.feltRect.height * 0.3, root.feltRect.height * 0.7)
            }
        }
    }

    // Woven texture: tiled noise masked to the felt.
    Image {
        id: feltTexture
        x: root.feltRect.x
        y: root.feltRect.y
        width: root.feltRect.width
        height: root.feltRect.height
        source: Qt.resolvedUrl("../../assets/table/felt_noise.png")
        fillMode: Image.Tile
        visible: false
    }
    Rectangle {
        id: feltMask
        x: root.feltRect.x
        y: root.feltRect.y
        width: root.feltRect.width
        height: root.feltRect.height
        radius: height / 2
        visible: false
        layer.enabled: true
    }
    MultiEffect {
        source: feltTexture
        anchors.fill: feltTexture
        maskEnabled: true
        maskSource: feltMask
        opacity: 0.55
    }
}
