import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import PokerPractice.Bridge
import "../components"

Rectangle {
    id: root

    signal playRequested()
    signal newSessionRequested()
    signal statisticsRequested()
    signal historyRequested()
    signal settingsRequested()

    color: Theme.background

    // Soft felt-coloured glow fading into the background.
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer

        ShapePath {
            strokeWidth: 0
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: root.width / 2
                centerY: root.height * 0.45
                centerRadius: Math.max(root.width, root.height) * 0.55
                focalX: centerX
                focalY: centerY
                GradientStop { position: 0.0; color: "#17382a" }
                GradientStop { position: 0.55; color: "#151d19" }
                GradientStop { position: 1.0; color: Theme.background }
            }
            startX: 0; startY: 0
            PathLine { x: root.width; y: 0 }
            PathLine { x: root.width; y: root.height }
            PathLine { x: 0; y: root.height }
            PathLine { x: 0; y: 0 }
        }
    }

    ColumnLayout {
        id: column
        anchors.centerIn: parent
        spacing: Theme.spacing

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: App.name
            font.family: Theme.fontDisplay
            font.pixelSize: Math.max(Theme.fontSizeTitle, Math.min(root.width / 22, 52))
            color: Theme.textPrimary
        }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: 120
            Layout.preferredHeight: 1
            color: Theme.gold
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            Layout.bottomMargin: Theme.spacingLarge
            text: "TEXAS HOLD'EM  ·  PRACTICE TABLE"
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeSmall
            font.letterSpacing: 3
            color: Theme.gold
        }

        MenuButton {
            objectName: "playButton"
            Layout.alignment: Qt.AlignHCenter
            text: Game.sessionActive ? "Resume Table" : "Play"
            primary: true
            onClicked: root.playRequested()
        }
        MenuButton {
            objectName: "newSessionMenuButton"
            Layout.alignment: Qt.AlignHCenter
            visible: Game.sessionActive
            text: "New Session"
            onClicked: root.newSessionRequested()
        }
        MenuButton {
            objectName: "statisticsButton"
            Layout.alignment: Qt.AlignHCenter
            text: "Statistics"
            onClicked: root.statisticsRequested()
        }
        MenuButton {
            objectName: "historyButton"
            Layout.alignment: Qt.AlignHCenter
            text: "Hand History"
            onClicked: root.historyRequested()
        }
        MenuButton {
            objectName: "settingsButton"
            Layout.alignment: Qt.AlignHCenter
            text: "Settings"
            onClicked: root.settingsRequested()
        }
        MenuButton {
            objectName: "quitButton"
            Layout.alignment: Qt.AlignHCenter
            text: "Quit"
            onClicked: App.requestQuit()
        }
    }

    Rectangle {
        objectName: "startupNotice"
        anchors { horizontalCenter: parent.horizontalCenter; top: parent.top; topMargin: Theme.spacingLarge }
        visible: Settings.recoveryNotice !== ""
        width: Math.min(parent.width - 48, noticeText.implicitWidth + 32)
        height: noticeText.implicitHeight + 16
        radius: Theme.radius
        color: "#3a2a1a"
        border.color: Theme.goldDim
        Text {
            id: noticeText
            anchors.centerIn: parent
            width: Math.min(implicitWidth, parent.parent.width - 80)
            wrapMode: Text.WordWrap
            text: Settings.recoveryNotice
            font.family: Theme.fontBody
            font.pixelSize: Theme.fontSizeSmall
            color: Theme.textPrimary
        }
    }

    Text {
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: Theme.spacingLarge }
        text: "Virtual chips only — no real-money gambling.   v" + App.version
        font.family: Theme.fontBody
        font.pixelSize: Theme.fontSizeSmall
        color: Theme.textMuted
    }
}
