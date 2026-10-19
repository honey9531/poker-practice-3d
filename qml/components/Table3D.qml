import QtQuick
import QtQuick3D
import QtQuick.Window
import PokerPractice.Bridge

// The poker table as a 3D scene: felt, rail, cards, chips and position pucks.
// Names, amounts and messages stay 2D: the parent places them with
// ``pointAt()``, which projects table positions into this item's coordinates.
//
// Positions use the same system as the 2D table: [u, v] fractions of the
// table's outer rectangle, u from left to right and v from the far side (0)
// to the human's side (1).
Item {
    id: root

    property var game
    property bool animated: true
    property bool dealing: false  // a hand has just started: deal hole cards in
    // Rendering on the CPU (no GPU driver): drop shadows, ambient occlusion and multisampling.
    property bool lowPower: false
    property var seatPoints: []
    property var betPoints: []
    property var markerPoints: []

    // Hole cards sit on the felt in front of each display slot.
    readonly property var holePoints: [[0.5, 0.79], [0.21, 0.7], [0.22, 0.38], [0.34, 0.22], [0.78, 0.38], [0.79, 0.7]]
    readonly property var potPoint: [0.5, 0.27]
    readonly property var boardPoint: [0.5, 0.53]

    readonly property real boardCardWidth: 15.5
    readonly property real holeCardWidth: 10.5
    readonly property real humanCardWidth: 15

    // Camera: looks down at ``pitch`` degrees; distance and aim are fitted to the item.
    readonly property real pitch: 54
    readonly property real fieldOfView: 34
    readonly property var cameraFit: fitCamera(width, height)

    // Size unit for the 2D overlays, as on the 2D table: a twelfth of the table's width.
    readonly property real unit: {
        const left = projectFraction(0, 0.5), right = projectFraction(1, 0.5)
        return Math.max(52, Math.min(160, (right.x - left.x) / 12))
    }

    // Device pixels per scene unit at the human's cards (the nearest, so the largest
    // on screen); cards size their artwork from it.
    readonly property real cardPixelsPerUnit: {
        const z = world(holePoints[0]).z
        return (project(10, 0, z).x - project(0, 0, z).x) / 10 * Screen.devicePixelRatio
    }

    property bool ready: false
    Component.onCompleted: ready = true

    // Table dimensions, from the same module that builds the meshes. Created
    // with the root so bindings can use it while the scene is still being
    // built; the fallbacks only matter while the scene is being torn down.
    readonly property TableGeometry dims: TableGeometry {}
    readonly property real outerWidth: dims ? dims.outerWidth : 0
    readonly property real outerDepth: dims ? dims.outerDepth : 0
    readonly property real straightHalf: dims ? dims.straightHalf : 0
    readonly property real railHeight: dims ? dims.railHeight : 0
    readonly property real apronDepth: dims ? dims.apronDepth : 0

    function world(point, y) {
        return Qt.vector3d((point[0] - 0.5) * outerWidth, y || 0,
                           (point[1] - 0.5) * outerDepth)
    }

    // ------------------------------------------------------------ projection

    // Normalised device coordinates of a world point for a camera aimed at
    // (0, 0, targetZ) from ``distance`` away. Matches PerspectiveCamera with a
    // vertical field of view.
    function ndc(x, y, z, distance, targetZ, aspect) {
        const p = pitch * Math.PI / 180
        const vx = x
        const vy = y - distance * Math.sin(p)
        const vz = z - (targetZ + distance * Math.cos(p))
        const up = vy * Math.cos(p) - vz * Math.sin(p)
        const depth = -vy * Math.sin(p) - vz * Math.cos(p)
        const t = Math.tan(fieldOfView * Math.PI / 360)
        return { x: vx / (depth * t * aspect), y: up / (depth * t) }
    }

    function project(x, y, z) {
        const fit = cameraFit
        const n = ndc(x, y, z, fit.distance, fit.targetZ, width / Math.max(1, height))
        return Qt.point((n.x + 1) / 2 * width, (1 - n.y) / 2 * height)
    }

    // A table position ([u, v]) in this item's coordinates.
    function projectFraction(u, v, y) {
        const w = world([u, v], y)
        return project(w.x, w.y, w.z)
    }

    function pointAt(point) {
        return projectFraction(point[0], point[1], 0)
    }

    // Closest camera that shows the whole table plus the seats, with room for
    // the nameplates at the top and bottom, centred vertically.
    function fitCamera(w, h) {
        if (w <= 0 || h <= 0 || outerWidth <= 0)
            return { distance: 600, targetZ: 0 }
        const aspect = w / h
        const halfW = outerWidth / 2, halfD = outerDepth / 2
        const points = [
            [-halfW, railHeight, 0], [halfW, railHeight, 0],
            [-straightHalf, railHeight, -halfD],
            [straightHalf, railHeight, -halfD],
            [-straightHalf, -apronDepth, halfD],
            [straightHalf, -apronDepth, halfD],
            [-halfW * 0.9, -apronDepth, halfD * 0.45],
            [halfW * 0.9, -apronDepth, halfD * 0.45],
        ]
        for (const seat of seatPoints)
            points.push([(seat[0] - 0.5) * 2 * halfW, 0, (seat[1] - 0.5) * 2 * halfD])
        // Margins in NDC: sides, top (far nameplate), bottom (human nameplate and labels).
        const side = 1 - 2 * 0.035, top = 1 - 2 * 0.075, bottom = -1 + 2 * 0.11

        function extents(distance, targetZ) {
            let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9
            for (const p of points) {
                const n = ndc(p[0], p[1], p[2], distance, targetZ, aspect)
                minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x)
                minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y)
            }
            return { minX, maxX, minY, maxY }
        }
        function fits(e) {
            return e.minX >= -side && e.maxX <= side && e.maxY <= top && e.minY >= bottom
        }
        function closest(targetZ) {
            let near = 60, far = 5000
            for (let i = 0; i < 32; ++i) {
                const mid = (near + far) / 2
                if (fits(extents(mid, targetZ)))
                    far = mid
                else
                    near = mid
            }
            return far
        }
        // Balance the space above and below by moving the aim along z.
        function imbalance(targetZ) {
            const e = extents(closest(targetZ), targetZ)
            return (top - e.maxY) - (e.minY - bottom)
        }
        let z0 = 0, z1 = 10, f0 = imbalance(z0), f1 = imbalance(z1)
        for (let i = 0; i < 8 && Math.abs(f1) > 1e-4 && f1 !== f0; ++i) {
            const z2 = z1 - f1 * (z1 - z0) / (f1 - f0)
            z0 = z1; f0 = f1
            z1 = Math.max(-outerDepth, Math.min(outerDepth, z2))
            f1 = imbalance(z1)
        }
        return { distance: closest(z1), targetZ: z1 }
    }

    // ------------------------------------------------------------ chip flights

    readonly property vector3d potPosition: world(potPoint)

    function flyChips(amount, from, to) {
        if (!animated || amount <= 0)
            return
        flyingChips.createObject(scene, { amount: amount, startPosition: from, endPosition: to })
    }

    Component {
        id: flyingChips
        ChipPile3D {
            id: flyer
            property vector3d startPosition
            property vector3d endPosition
            property real progress: 0
            animated: false
            maxPerStack: 8
            maxStacks: 4
            perRow: 4
            position: Qt.vector3d(startPosition.x + (endPosition.x - startPosition.x) * progress,
                                  startPosition.y + (endPosition.y - startPosition.y) * progress
                                  + Math.sin(progress * Math.PI) * 9,
                                  startPosition.z + (endPosition.z - startPosition.z) * progress)
            NumberAnimation on progress {
                to: 1
                duration: 480
                easing.type: Easing.InOutCubic
                onFinished: flyer.destroy()
            }
        }
    }

    // ------------------------------------------------------------ scene

    View3D {
        id: view
        objectName: "tableView3d"
        anchors.fill: parent
        camera: camera

        environment: SceneEnvironment {
            objectName: "sceneEnvironment"
            backgroundMode: SceneEnvironment.Transparent
            antialiasingMode: root.lowPower ? SceneEnvironment.NoAA : SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
            aoEnabled: !root.lowPower
            aoStrength: 45
            aoDistance: 6
            aoSoftness: 40
            aoSampleRate: 3
        }

        PerspectiveCamera {
            id: camera
            fieldOfView: root.fieldOfView
            clipNear: 10
            clipFar: 4000
            position: Qt.vector3d(0, root.cameraFit.distance * Math.sin(root.pitch * Math.PI / 180),
                                  root.cameraFit.targetZ + root.cameraFit.distance * Math.cos(root.pitch * Math.PI / 180))
            eulerRotation.x: -root.pitch
        }

        // Key light from above and slightly behind the far side: soft shadows towards the player.
        DirectionalLight {
            eulerRotation: Qt.vector3d(-64, 12, 0)
            brightness: 0.75
            castsShadow: !root.lowPower
            shadowMapQuality: Light.ShadowMapQualityHigh
            shadowFactor: 45
            shadowMapFar: 600
            softShadowQuality: Light.PCF16
            pcfFactor: 1.5
            csmNumSplits: 0
        }
        // Overhead lamp: a pool of light on the felt that falls off towards the rail.
        SpotLight {
            position: Qt.vector3d(0, 240, 10)
            eulerRotation.x: -90
            coneAngle: 62
            innerConeAngle: 18
            brightness: 22
            quadraticFade: 0.6
            color: "#fff4e0"
        }
        // Fill so the near side of the rail and the cards' backs never go black.
        DirectionalLight {
            eulerRotation: Qt.vector3d(-30, 180, 0)
            brightness: 0.25
            color: "#dfe6ff"
        }

        Node {
            id: scene

            // Floor, far below: catches the table's shadow.
            Model {
                source: "#Rectangle"
                y: -75
                eulerRotation.x: -90
                scale: Qt.vector3d(30, 30, 1)
                materials: PrincipledMaterial { baseColor: "#121110"; roughness: 0.9 }
            }

            Model {
                objectName: "felt3d"
                geometry: TableGeometry { part: "felt" }
                materials: PrincipledMaterial {
                    baseColorMap: Texture {
                        sourceItem: Rectangle {
                            width: 256
                            height: 256
                            color: Theme.felt
                            Image {
                                anchors.fill: parent
                                source: Qt.resolvedUrl("../../assets/table/felt_noise.png")
                                opacity: 0.3
                            }
                        }
                        tilingModeHorizontal: Texture.Repeat
                        tilingModeVertical: Texture.Repeat
                        generateMipmaps: true
                        mipFilter: Texture.Linear
                    }
                    roughness: 0.95
                    specularAmount: 0.04
                }
            }
            Model {
                geometry: TableGeometry { part: "line" }
                materials: PrincipledMaterial {
                    baseColor: Qt.rgba(0.89, 0.76, 0.49, 0.3)
                    alphaMode: PrincipledMaterial.Blend
                    lighting: PrincipledMaterial.NoLighting
                }
            }
            Model {
                geometry: TableGeometry { part: "trim" }
                materials: PrincipledMaterial {
                    baseColor: "#6a4327"
                    roughness: 0.3
                    clearcoatAmount: 0.6
                    clearcoatRoughnessAmount: 0.15
                    cullMode: Material.NoCulling
                }
            }
            Model {
                objectName: "rail3d"
                geometry: TableGeometry { part: "rail" }
                materials: PrincipledMaterial {
                    baseColor: "#2b231e"
                    roughness: 0.48
                    specularAmount: 0.45
                    clearcoatAmount: 0.25
                    clearcoatRoughnessAmount: 0.35
                    cullMode: Material.NoCulling
                }
            }
            Model {
                geometry: TableGeometry { part: "apron" }
                materials: PrincipledMaterial {
                    baseColor: "#3a2516"
                    roughness: 0.4
                    clearcoatAmount: 0.4
                    cullMode: Material.NoCulling
                }
            }

            // Pot.
            ChipPile3D {
                objectName: "potChips3d"
                position: root.potPosition
                amount: root.game.pots.reduce((sum, p) => sum + p.amount, 0)
                maxPerStack: 10
                maxStacks: 6
                perRow: 3
                animated: root.animated
            }

            // Community cards: five places with a faint outline.
            Node {
                position: root.world(root.boardPoint)

                Repeater3D {
                    model: 5
                    Node {
                        id: boardSlot
                        required property int index
                        x: (index - 2) * root.boardCardWidth * 1.12

                        Model {
                            source: "#Rectangle"
                            y: 0.05
                            eulerRotation.x: -90
                            scale: Qt.vector3d(root.boardCardWidth / 100, root.boardCardWidth * 88 / 63 / 100, 1)
                            materials: PrincipledMaterial {
                                baseColor: Qt.rgba(0, 0, 0, 0.09)
                                alphaMode: PrincipledMaterial.Blend
                                lighting: PrincipledMaterial.NoLighting
                            }
                        }

                        Card3D {
                            id: boardCard
                            objectName: "boardCard3d" + boardSlot.index
                            readonly property string code: boardSlot.index < root.game.board.length
                                                            ? root.game.board[boardSlot.index] : ""
                            property bool landed: true
                            visible: code !== ""
                            card: code
                            faceUp: landed
                            highlighted: code !== "" && root.game.winningCards.indexOf(code) >= 0
                            animated: root.animated
                            cardWidth: root.boardCardWidth
                            pixelsPerUnit: root.cardPixelsPerUnit

                            Timer {
                                id: flipTimer
                                onTriggered: boardCard.landed = true
                            }
                            // Slide in face down from the far side, then turn over (flop cards one after another).
                            onCodeChanged: {
                                if (code === "" || !root.animated || !root.ready) {
                                    landed = true
                                    return
                                }
                                const delay = boardSlot.index < 3 ? boardSlot.index * 110 : 0
                                landed = false
                                dealFrom(Qt.vector3d(0, 0, -cardHeight * 0.9), delay)
                                flipTimer.interval = delay + 360
                                flipTimer.restart()
                            }
                        }
                    }
                }
            }

            // Hole cards, bets and position pucks for every seat.
            Repeater3D {
                model: root.game.players

                Node {
                    id: seat
                    required property int slot
                    required property var cards
                    required property int bet
                    required property int wonAmount
                    required property bool folded
                    required property bool isHuman
                    required property bool isDealer
                    required property bool isSmallBlind
                    required property bool isBigBlind
                    required property var bestCards

                    readonly property vector3d home: root.world(root.holePoints[slot])
                    readonly property vector3d seatPosition: root.world(root.seatPoints[slot])
                    readonly property real cardWidth: isHuman ? root.humanCardWidth : root.holeCardWidth

                    property int previousWon: 0
                    onWonAmountChanged: {
                        if (wonAmount > previousWon)
                            root.flyChips(wonAmount - previousWon, root.potPosition, home)
                        previousWon = wonAmount
                    }

                    Repeater3D {
                        model: 2
                        Card3D {
                            id: hole
                            required property int index
                            readonly property bool present: index < seat.cards.length
                            readonly property string code: present ? seat.cards[index] : ""
                            // Face down until it has landed in front of the player.
                            property bool landed: true
                            objectName: "holeCard3d_" + seat.slot + "_" + index
                            visible: present
                            position: Qt.vector3d(seat.home.x + (index - 0.5) * seat.cardWidth * (seat.isHuman ? 1.06 : 0.7),
                                                  index * 0.12,
                                                  seat.home.z)
                            eulerRotation.y: (0.5 - index) * (seat.isHuman ? 3 : 7)
                            cardWidth: seat.cardWidth
                            pixelsPerUnit: root.cardPixelsPerUnit
                            // The human's cards lean towards the camera; so do opponents' cards once shown.
                            tilt: seat.isHuman ? 30 : (showingFace ? 30 : 0)
                            opacity: seat.folded ? 0.45 : 1
                            card: code
                            faceUp: code !== "" && landed
                            highlighted: code !== "" && seat.bestCards.indexOf(code) >= 0
                            animated: root.animated

                            Behavior on tilt {
                                enabled: root.animated
                                NumberAnimation { duration: 340; easing.type: Easing.InOutQuad }
                            }

                            Timer {
                                id: landTimer
                                onTriggered: hole.landed = true
                            }
                            function deal() {
                                if (!present || !root.dealing) {
                                    landed = true
                                    return
                                }
                                const delay = (index * 6 + seat.slot) * 60
                                landed = false
                                dealFrom(root.world(root.boardPoint).minus(position), delay)
                                landTimer.interval = delay + 420
                                landTimer.restart()
                            }
                            onPresentChanged: deal()
                            Component.onCompleted: deal()
                        }
                    }

                    ChipPile3D {
                        id: betPile
                        objectName: "betChips3d_" + seat.slot
                        property int previous: 0
                        position: root.world(root.betPoints[seat.slot])
                        amount: seat.bet
                        maxPerStack: 8
                        maxStacks: 4
                        perRow: 4
                        animated: root.animated
                        onAmountChanged: {
                            if (amount > previous && previous === 0)
                                animateFrom(seat.seatPosition.minus(position), 0)
                            else if (amount < previous)
                                root.flyChips(previous - amount, position, root.potPosition)
                            previous = amount
                        }
                        Component.onCompleted: previous = amount
                    }

                    Node {
                        position: root.world(root.markerPoints[seat.slot])
                        Puck3D { kind: "D"; visible: seat.isDealer }
                        Puck3D { kind: "SB"; x: seat.isDealer ? 6 : 0; visible: seat.isSmallBlind }
                        Puck3D { kind: "BB"; x: seat.isDealer ? 6 : 0; visible: seat.isBigBlind }
                    }
                }
            }
        }
    }
}
