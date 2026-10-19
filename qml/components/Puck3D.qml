import QtQuick
import QtQuick3D

// Dealer button ("D") or blind marker ("SB" / "BB") as a puck on the felt.
// The top face reuses the 2D PositionMarker artwork.
Node {
    id: root

    property string kind: "D"
    property real size: kind === "D" ? 5.6 : 4.6  // diameter
    readonly property real thickness: kind === "D" ? 1.1 : 0.8

    Model {
        source: "#Cylinder"
        y: root.thickness / 2
        scale: Qt.vector3d(root.size / 100, root.thickness / 100, root.size / 100)
        materials: PrincipledMaterial {
            baseColor: root.kind === "D" ? "#e9e3d5" : (root.kind === "SB" ? "#35618f" : "#b28934")
            roughness: 0.35
        }
    }

    Model {
        source: "#Rectangle"
        y: root.thickness + 0.01
        eulerRotation.x: -90
        scale: Qt.vector3d(root.size / 100, root.size / 100, 1)
        materials: PrincipledMaterial {
            baseColorMap: Texture {
                sourceItem: Item {
                    width: 128
                    height: 128
                    PositionMarker {
                        // The 2D marker draws a drop shadow below itself; keep it out of the texture.
                        anchors.fill: parent
                        anchors.margins: 1
                        kind: root.kind
                        size: 126
                    }
                }
            }
            alphaMode: PrincipledMaterial.Mask
            alphaCutoff: 0.6
            roughness: 0.35
        }
    }
}
