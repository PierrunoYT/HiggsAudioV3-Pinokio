module.exports = {
  version: "7.0",
  menu: async (kernel, info) => {
    let installed = info.exists("app/env") && info.exists("app/sglang-omni") && info.exists("app/models/higgs-audio-v3-tts-4b")
    let running = {
      install: info.running("install.js"),
      start: info.running("start.js"),
      backend: info.running("backend.js"),
      update: info.running("update.js"),
      reset: info.running("reset.js")
    }
    if (running.install) {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Installing",
        href: "install.js",
      }]
    } else if (installed) {
      if (running.start) {
        let local = info.local("start.js")
        if (local && local.url) {
          return [{
            default: true,
            icon: "fa-solid fa-rocket",
            text: "Open Web UI",
            href: local.url,
          }, {
            icon: "fa-solid fa-terminal",
            text: "Terminal",
            href: "start.js",
          }, {
            icon: "fa-solid fa-server",
            text: "Backend Terminal",
            href: "backend.js",
          }]
        } else {
          return [{
            default: true,
            icon: "fa-solid fa-terminal",
            text: "Terminal",
            href: "start.js",
          }]
        }
      } else if (running.update) {
        return [{
          default: true,
          icon: "fa-solid fa-terminal",
          text: "Updating",
          href: "update.js",
        }]
      } else if (running.reset) {
        return [{
          default: true,
          icon: "fa-solid fa-terminal",
          text: "Resetting",
          href: "reset.js",
        }]
      } else {
        let items = [{
          default: true,
          icon: "fa-solid fa-power-off",
          text: "Start UI",
          href: "start.js",
        }, {
          icon: "fa-solid fa-server",
          text: "Start Backend",
          href: "backend.js",
        }, {
          icon: "fa-solid fa-plug",
          text: "Update",
          href: "update.js",
        }, {
          icon: "fa-solid fa-plug",
          text: "Install",
          href: "install.js",
        }, {
          icon: "fa-regular fa-circle-xmark",
          text: "<div><strong>Reset</strong><div>Revert to pre-install state</div></div>",
          href: "reset.js",
          confirm: "Are you sure you wish to reset the app?"
        }]
        if (running.backend) {
          items[1] = {
            icon: "fa-solid fa-terminal",
            text: "Backend Terminal",
            href: "backend.js",
          }
        }
        return items
      }
    } else {
      return [{
        default: true,
        icon: "fa-solid fa-plug",
        text: "Install",
        href: "install.js",
      }]
    }
  }
}
