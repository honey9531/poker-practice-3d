import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Window
import PokerPractice.Bridge
import "components"
import "screens"

ApplicationWindow {
    id: window
    objectName: "mainWindow"

    width: 1280
    height: 800
    minimumWidth: 1024
    minimumHeight: 640
    visible: true
    title: App.name
    color: Theme.background

    // Name of the screen on top of the stack, for navigation and tests.
    property string currentScreen: "menu"

    function showScreen(name) {
        if (name === currentScreen)
            return
        const component = {
            "table": tableScreen,
            "statistics": statisticsScreen,
            "history": historyScreen,
            "settings": settingsScreen,
            "setup": setupScreen,
            "replay": replayScreen,
            "gallery": galleryScreen
        }[name]
        const animate = Settings.animationsEnabled
        if (name === "menu") {
            stack.pop(null, animate ? StackView.PopTransition : StackView.Immediate)
        } else if (component) {
            stack.pop(null, StackView.Immediate)
            stack.push(component, {}, animate ? StackView.PushTransition : StackView.Immediate)
        } else {
            console.warn("Unknown screen", name)
            return
        }
        currentScreen = name
    }

    // ------------------------------------------------------------ geometry
    // Restore the last window size/position if it still fits on a screen.
    function restoreGeometry() {
        const g = Settings.windowGeometry
        if (g.width === undefined)
            return
        const fits = g.x >= -50 && g.y >= -50
                  && g.x + 100 <= Screen.desktopAvailableWidth && g.y + 100 <= Screen.desktopAvailableHeight
        width = Math.max(minimumWidth, g.width)
        height = Math.max(minimumHeight, g.height)
        if (fits) {
            x = g.x
            y = g.y
        }
        if (g.maximized)
            visibility = Window.Maximized
    }

    function saveGeometry() {
        const maximized = visibility === Window.Maximized
        Settings.saveWindowGeometry({ x: x, y: y, width: width, height: height, maximized: maximized })
    }

    Component.onCompleted: restoreGeometry()
    onClosing: saveGeometry()

    // ------------------------------------------------------------ screens
    StackView {
        id: stack
        objectName: "screenStack"
        anchors.fill: parent

        initialItem: MainMenuScreen {
            onPlayRequested: window.showScreen(Game.sessionActive ? "table" : "setup")
            onNewSessionRequested: window.showScreen("setup")
            onStatisticsRequested: window.showScreen("statistics")
            onHistoryRequested: window.showScreen("history")
            onSettingsRequested: window.showScreen("settings")
        }

        pushEnter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.durationNormal }
        }
        pushExit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.durationNormal }
        }
        popEnter: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.durationNormal }
        }
        popExit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.durationNormal }
        }
    }

    Component {
        id: tableScreen
        TableScreen {
            onBackRequested: window.showScreen("menu")
            onActionRequested: (kind, amount, step) => Game.submitAction(kind, amount, step)
            animated: Settings.animationsEnabled
            onDealRequested: Game.deal()
            onNewSessionRequested: window.showScreen("setup")
            onSessionEnded: window.showScreen("menu")
        }
    }
    Component { id: statisticsScreen; StatisticsScreen { onBackRequested: window.showScreen("menu") } }
    Component {
        id: historyScreen
        HistoryScreen {
            onBackRequested: window.showScreen("menu")
            onReplayRequested: handId => {
                if (Replay.load(handId))
                    window.showScreen("replay")
            }
        }
    }
    Component {
        id: replayScreen
        TableScreen {
            game: Replay
            replayMode: true
            animated: false
            onBackRequested: {
                Replay.stop()
                window.showScreen("history")
            }
        }
    }
    Component { id: settingsScreen; SettingsScreen { onBackRequested: window.showScreen("menu") } }
    Component {
        id: setupScreen
        SessionSetupScreen {
            defaults: Settings.sessionDefaults
            onBackRequested: window.showScreen("menu")
            onStartRequested: config => {
                Settings.saveSessionDefaults(config)
                if (Game.startSession(config))
                    window.showScreen("table")
            }
        }
    }
    Component { id: galleryScreen; GalleryScreen { onBackRequested: window.showScreen("menu") } }

    // ------------------------------------------------------------ feedback
    // Recoverable problems from any part of the app (rejected actions, storage errors).
    ErrorToast {
        id: toast
        objectName: "errorToast"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 132
        z: 100
    }
    Connections { target: Game; function onErrorOccurred(message) { toast.show(message) } }
    Connections { target: Replay; function onErrorOccurred(message) { toast.show(message) } }
    Connections { target: Settings; function onErrorOccurred(message) { toast.show(message) } }
    Connections { target: Stats; function onErrorOccurred(message) { toast.show(message) } }

    // Unexpected internal errors: logged in Python, explained here.
    ConfirmDialog {
        id: errorDialog
        objectName: "errorDialog"
        title: "Something went wrong"
        cancelText: "Close"
        confirmText: "Continue"
    }
    Connections {
        target: App
        function onErrorReported(message) {
            errorDialog.text = message + "\n\nThe details were written to the log file:\n" + App.logFile
            errorDialog.open()
        }
    }

    // Developer shortcut to the card/chip gallery.
    Shortcut {
        sequence: "Ctrl+Shift+G"
        onActivated: window.showScreen("gallery")
    }
}
