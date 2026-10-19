import QtQuick
import QtQuick3D
import PokerPractice.Bridge

// A playing card lying on the 3D table, its top edge pointing away from the
// camera. An empty ``card`` always shows the back. The card flips over its
// long axis, can be tilted up towards the camera, and can slide in when dealt.
Node {
    id: root

    // "As", "Td", ... ; empty means an unknown card.
    property string card: ""
    property bool faceUp: true
    property bool highlighted: false
    property bool animated: true
    property real cardWidth: 14
    // Degrees the far edge is raised towards the camera (0 = flat on the felt).
    property real tilt: 0

    readonly property real cardHeight: cardWidth * 88 / 63
    readonly property bool showingFace: card !== "" && faceUp

    // 0 = face up, 180 = face down.
    property real flip: showingFace ? 0 : 180
    Behavior on flip {
        enabled: root.animated
        NumberAnimation { duration: 340; easing.type: Easing.InOutQuad }
    }

    property real lift: highlighted ? cardWidth * 0.09 : 0
    Behavior on lift {
        enabled: root.animated
        NumberAnimation { duration: Theme.durationNormal; easing.type: Easing.OutCubic }
    }

    // Deal: slide in from ``dealOffset`` (relative to the resting position).
    property vector3d dealOffset: Qt.vector3d(0, 0, 0)
    property real dealProgress: 1
    property bool waiting: false  // hidden until its deal starts

    function dealFrom(offset, delay) {
        dealAnimation.stop()
        dealOffset = offset
        if (!animated) {
            dealProgress = 1
            waiting = false
            return
        }
        dealProgress = 0
        waiting = true
        pause.duration = delay || 0
        dealAnimation.start()
    }

    SequentialAnimation {
        id: dealAnimation
        PauseAnimation { id: pause }
        PropertyAction { target: root; property: "waiting"; value: false }
        NumberAnimation { target: root; property: "dealProgress"; to: 1; duration: 380; easing.type: Easing.OutCubic }
    }

    Node {
        id: travel
        visible: !root.waiting
        position: Qt.vector3d(root.dealOffset.x * (1 - root.dealProgress),
                              root.dealOffset.y * (1 - root.dealProgress) + Math.sin(root.dealProgress * Math.PI) * 4,
                              root.dealOffset.z * (1 - root.dealProgress))

        // Raise the card on its near edge so tilting never sinks it into the felt.
        Node {
            y: 0.15 + root.lift + root.cardHeight / 2 * Math.sin(root.tilt * Math.PI / 180)
            eulerRotation.x: root.tilt

            Node {
                id: flipper
                // Lift while turning over so the card clears the felt.
                y: Math.abs(Math.sin(root.flip * Math.PI / 180)) * root.cardWidth / 2
                eulerRotation.z: root.flip

                Model {
                    objectName: "cardFace"
                    source: "#Rectangle"
                    y: 0.03
                    eulerRotation.x: -90
                    scale: Qt.vector3d(root.cardWidth / 100, root.cardHeight / 100, 1)
                    visible: root.card !== ""
                    materials: PrincipledMaterial {
                        baseColorMap: Texture {
                            source: root.card !== "" ? Qt.resolvedUrl("../../assets/cards/" + root.card + ".svg") : ""
                            generateMipmaps: true
                            mipFilter: Texture.Linear
                        }
                        alphaMode: PrincipledMaterial.Mask
                        alphaCutoff: 0.5
                        roughness: 0.55
                        specularAmount: 0.2
                    }
                }

                Model {
                    source: "#Rectangle"
                    y: -0.03
                    eulerRotation.x: 90
                    scale: Qt.vector3d(root.cardWidth / 100, root.cardHeight / 100, 1)
                    materials: PrincipledMaterial {
                        baseColorMap: cardBack
                        alphaMode: PrincipledMaterial.Mask
                        alphaCutoff: 0.5
                        roughness: 0.5
                        specularAmount: 0.25
                    }
                }

                // Gold rim around a highlighted (winning) card.
                Model {
                    objectName: "highlightRim"
                    source: "#Rectangle"
                    eulerRotation.x: -90
                    scale: Qt.vector3d(root.cardWidth * 1.1 / 100, root.cardHeight * 1.075 / 100, 1)
                    visible: root.highlighted && root.showingFace
                    materials: PrincipledMaterial {
                        baseColor: Theme.goldBright
                        emissiveFactor: Qt.vector3d(0.85, 0.68, 0.32)
                        opacityMap: cardBack
                        opacityChannel: Material.A
                        alphaMode: PrincipledMaterial.Mask
                        alphaCutoff: 0.5
                        lighting: PrincipledMaterial.NoLighting
                    }
                }
            }
        }
    }

    Texture {
        id: cardBack
        source: Qt.resolvedUrl("../../assets/cards/back_" + Settings.cardBack + ".svg")
        generateMipmaps: true
        mipFilter: Texture.Linear
    }
}
