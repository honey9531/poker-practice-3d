import QtQuick
import QtQuick3D
import PokerPractice.Bridge

// An amount as stacks of 3D chips standing on the felt, largest denomination
// first, in rows of ``perRow`` centred on this node.
// Display only: ``amount`` comes from the engine and is never modified here.
Node {
    id: root

    property int amount: 0
    property real chipSize: 4.2  // diameter
    property int maxPerStack: 10
    property int maxStacks: 6
    property int perRow: 3
    property bool animated: true

    readonly property real thickness: chipSize * 0.17
    readonly property real spacing: chipSize * 1.1

    // [{value, label, color, insert, text, count}] split into display stacks.
    readonly property var stacks: {
        Chips.denominations  // re-evaluate when the colour scheme changes
        const result = []
        for (const entry of Chips.breakdown(amount)) {
            let remaining = entry.count
            while (remaining > 0 && result.length < maxStacks) {
                const n = Math.min(remaining, maxPerStack)
                result.push(Object.assign({}, entry, { count: n }))
                remaining -= n
            }
        }
        return result
    }

    // Slide in from ``offset`` (relative to the resting position).
    property vector3d motionOffset: Qt.vector3d(0, 0, 0)
    property real motionProgress: 1

    function animateFrom(offset, delay) {
        motion.stop()
        motionOffset = offset
        if (!animated) {
            motionProgress = 1
            return
        }
        motionProgress = 0
        pause.duration = delay || 0
        motion.start()
    }

    SequentialAnimation {
        id: motion
        PauseAnimation { id: pause }
        NumberAnimation { target: root; property: "motionProgress"; to: 1; duration: 420; easing.type: Easing.OutCubic }
    }

    Node {
        position: Qt.vector3d(root.motionOffset.x * (1 - root.motionProgress),
                              root.motionOffset.y * (1 - root.motionProgress) + Math.sin(root.motionProgress * Math.PI) * 3,
                              root.motionOffset.z * (1 - root.motionProgress))

        Repeater3D {
            model: root.stacks

            Node {
                id: stack
                required property var modelData
                required property int index

                readonly property int rows: Math.ceil(root.stacks.length / root.perRow)
                readonly property int row: Math.floor(index / root.perRow)
                readonly property int column: index % root.perRow
                readonly property int inRow: Math.min(root.perRow, root.stacks.length - row * root.perRow)

                x: (column - (inRow - 1) / 2) * root.spacing
                z: (row - (rows - 1) / 2) * root.spacing * 0.95

                // Edge stripes: alternating base colour and inserts around the rim.
                PrincipledMaterial {
                    id: edgeMaterial
                    baseColorMap: Texture {
                        sourceItem: Row {
                            width: 192
                            height: 16
                            Repeater {
                                model: 12
                                Rectangle {
                                    width: 16
                                    height: 16
                                    color: index % 2 ? stack.modelData.insert : stack.modelData.color
                                }
                            }
                        }
                    }
                    roughness: 0.4
                    specularAmount: 0.35
                }

                Repeater3D {
                    model: stack.modelData.count
                    Model {
                        required property int index
                        source: "#Cylinder"
                        // Slightly untidy, like real chips.
                        x: ((index * 37) % 5 - 2) * root.chipSize * 0.012
                        z: ((index * 23) % 5 - 2) * root.chipSize * 0.012
                        y: root.thickness * (index + 0.5)
                        eulerRotation.y: (index * 47) % 360
                        scale: Qt.vector3d(root.chipSize / 100, root.thickness / 100, root.chipSize / 100)
                        materials: [edgeMaterial]
                    }
                }

                // Face of the top chip.
                Model {
                    source: "#Rectangle"
                    readonly property int top: stack.modelData.count - 1
                    x: ((top * 37) % 5 - 2) * root.chipSize * 0.012
                    z: ((top * 23) % 5 - 2) * root.chipSize * 0.012
                    y: root.thickness * stack.modelData.count + 0.01
                    eulerRotation.x: -90
                    scale: Qt.vector3d(root.chipSize / 100, root.chipSize / 100, 1)
                    materials: PrincipledMaterial {
                        baseColorMap: Texture {
                            sourceItem: PokerChip {
                                width: 128
                                height: 128
                                baseColor: stack.modelData.color
                                insertColor: stack.modelData.insert
                                textColor: stack.modelData.text
                                label: stack.modelData.label
                            }
                        }
                        alphaMode: PrincipledMaterial.Mask
                        alphaCutoff: 0.5
                        roughness: 0.4
                        specularAmount: 0.35
                    }
                }
            }
        }
    }
}
