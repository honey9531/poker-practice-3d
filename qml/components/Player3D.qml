import QtQuick
import QtQuick3D

// A computer opponent as a seated 3D character (assets/avatars/<character>).
//
// The node's origin is the middle of the seat at felt height, and the
// character faces +z (towards the table). The imported models stand in a
// rest pose; every time an expression value changes, the pose is rebuilt
// from that rest pose in scene space: thighs forward and calves down for
// sitting, the spine leaning, the head turning and nodding, and the arms
// solved with two-bone IK so the hands rest on the rail.
Node {
    id: root

    property string character: ""
    property bool animated: true
    property bool breathing: animated

    // Seat geometry, in this node's coordinates.
    property real seatHeight: -28  // where the pelvis rests
    property real handReach: 22  // forward distance to where the hands rest
    property real handHeight: 8  // height of the rail's top
    property real handSpread: 15  // each hand's distance from the middle

    // Expression, in degrees (smoothed): lean forwards (+) or back (-), nod
    // down (+) or up (-); the head turns towards ``lookAt`` (scene position).
    property real lean: 0
    property real nod: 0
    property vector3d lookAt: Qt.vector3d(0, 0, 0)
    property bool looking: false

    readonly property bool ready: loader.status === Loader3D.Ready

    property real smoothLean: lean
    property real smoothNod: nod
    property real lookYaw: 0
    property real breath: 0
    Behavior on smoothLean { enabled: root.animated; NumberAnimation { duration: 600; easing.type: Easing.InOutSine } }
    Behavior on smoothNod { enabled: root.animated; NumberAnimation { duration: 500; easing.type: Easing.InOutSine } }
    Behavior on lookYaw { enabled: root.animated; NumberAnimation { duration: 450; easing.type: Easing.InOutSine } }

    SequentialAnimation on breath {
        running: root.breathing && root.ready
        loops: Animation.Infinite
        NumberAnimation { from: 0; to: 1; duration: 1900; easing.type: Easing.InOutSine }
        NumberAnimation { from: 1; to: 0; duration: 2300; easing.type: Easing.InOutSine }
    }

    onSmoothLeanChanged: pose()
    onSmoothNodChanged: pose()
    onLookYawChanged: pose()
    onBreathChanged: pose()
    onLookAtChanged: updateLook()
    onLookingChanged: updateLook()
    // The pose is built along scene-space directions, so it must follow the seat when it moves or turns.
    onSceneTransformChanged: {
        updateLook()
        pose()
    }

    Loader3D {
        id: loader
        source: root.character !== ""
                ? Qt.resolvedUrl("../../assets/avatars/" + root.character + "/Avatar" + root.character + ".qml") : ""
        onLoaded: root.capture()
    }

    readonly property var boneNames: [
        "pelvis", "spine", "spine1", "spine2", "neck", "head",
        "leftClavicle", "leftUpperArm", "leftForearm", "leftHand", "leftFinger",
        "rightClavicle", "rightUpperArm", "rightForearm", "rightHand", "rightFinger",
        "leftThigh", "leftCalf", "leftFoot", "rightThigh", "rightCalf", "rightFoot"]
    property var restRotations: ({})

    // Remember the rest pose and sit the character down.
    function capture() {
        const avatar = loader.item
        // Copies: a stored property value can stay a live reference to the
        // bone's rotation, which would make every pose build on the last one.
        const rest = {}
        for (const name of boneNames) {
            const q = avatar[name].rotation
            rest[name] = Qt.quaternion(q.scalar, q.x, q.y, q.z)
        }
        restRotations = rest
        loader.y = 0
        const pelvis = root.mapPositionFromScene(avatar.pelvis.scenePosition)
        loader.y = seatHeight - pelvis.y
        updateLook()
        pose()
    }

    function updateLook() {
        if (!looking) {
            lookYaw = 0
            return
        }
        const local = root.mapPositionFromScene(lookAt)
        const yaw = Math.atan2(local.x, local.z) * 180 / Math.PI
        lookYaw = Math.max(-55, Math.min(55, yaw))
    }

    // Rotate ``bone`` (in scene space) so that the direction to ``child`` points along ``direction``.
    function aim(bone, child, direction) {
        const current = child.scenePosition.minus(bone.scenePosition).normalized()
        const target = direction.normalized()
        const axis = current.crossProduct(target)
        const sine = axis.length()
        if (sine < 1e-6)
            return
        const angle = Math.atan2(sine, current.dotProduct(target)) * 180 / Math.PI
        bone.rotate(angle, axis.normalized(), Node.SceneSpace)
    }

    // Two-bone IK: place ``end`` at ``target`` with the middle joint bending towards ``pole``.
    function reach(upper, lower, end, target, pole) {
        const start = upper.scenePosition
        const l1 = lower.scenePosition.minus(start).length()
        const l2 = end.scenePosition.minus(lower.scenePosition).length()
        const toTarget = target.minus(start)
        const distance = Math.max(Math.abs(l1 - l2) + 0.01, Math.min(toTarget.length(), (l1 + l2) * 0.999))
        const dir = toTarget.normalized()
        const along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
        const height = Math.sqrt(Math.max(0, l1 * l1 - along * along))
        const bend = pole.minus(dir.times(pole.dotProduct(dir))).normalized()
        const joint = start.plus(dir.times(along)).plus(bend.times(height))
        aim(upper, lower, joint.minus(start))
        aim(lower, end, start.plus(dir.times(distance)).minus(lower.scenePosition))
    }

    function pose() {
        const avatar = loader.item
        if (!avatar || !restRotations.pelvis)
            return
        for (const name of boneNames) {
            const q = restRotations[name]
            avatar[name].rotation = Qt.quaternion(q.scalar, q.x, q.y, q.z)
        }

        const side = root.mapDirectionToScene(Qt.vector3d(1, 0, 0)).normalized()
        const up = root.mapDirectionToScene(Qt.vector3d(0, 1, 0)).normalized()
        const forward = root.mapDirectionToScene(Qt.vector3d(0, 0, 1)).normalized()
        const origin = root.scenePosition

        // Sit: thighs forward and slightly apart, calves down.
        for (const [thigh, calf, foot] of [[avatar.leftThigh, avatar.leftCalf, avatar.leftFoot],
                                           [avatar.rightThigh, avatar.rightCalf, avatar.rightFoot]]) {
            const outward = Math.sign(thigh.scenePosition.minus(origin).dotProduct(side))
            aim(thigh, calf, forward.plus(side.times(outward * 0.14)).plus(up.times(-0.06)))
            aim(calf, foot, up.times(-1).plus(forward.times(0.12)))
        }

        // Torso: a slight natural forward lean plus the expression's (rotating about
        // the character's left-right axis), plus breathing.
        const leanAxis = side.times(-1)
        avatar.spine.rotate(4 + smoothLean * 0.45, leanAxis, Node.SceneSpace)
        avatar.spine1.rotate(smoothLean * 0.35, leanAxis, Node.SceneSpace)
        avatar.spine2.rotate(-breath * 1.2, leanAxis, Node.SceneSpace)

        // Head: turn towards what the character watches, then nod.
        avatar.neck.rotate(lookYaw * 0.35, up, Node.SceneSpace)
        avatar.head.rotate(lookYaw * 0.65, up, Node.SceneSpace)
        avatar.head.rotate(smoothNod, leanAxis, Node.SceneSpace)

        // Arms: forearms on the rail, elbows out and down, hands draped over the edge.
        for (const [upper, lower, hand, finger] of [
                 [avatar.leftUpperArm, avatar.leftForearm, avatar.leftHand, avatar.leftFinger],
                 [avatar.rightUpperArm, avatar.rightForearm, avatar.rightHand, avatar.rightFinger]]) {
            const outward = Math.sign(upper.scenePosition.minus(origin).dotProduct(side))
            const target = root.mapPositionToScene(Qt.vector3d(outward * handSpread, handHeight, handReach))
            const pole = side.times(outward * 0.9).plus(up.times(-1)).plus(forward.times(-0.3))
            reach(upper, lower, hand, target, pole)
            const along = hand.scenePosition.minus(lower.scenePosition).normalized()
            aim(hand, finger, along.plus(up.times(-0.75)).plus(side.times(-outward * 0.25)))
        }
    }
}
