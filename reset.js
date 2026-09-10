module.exports = {
  run: [
    {
      when: "{{exists('app/.installed')}}",
      method: "fs.rm",
      params: { path: "app/.installed" }
    },
    {
      method: "fs.rm",
      params: { path: "app/ui-env" }
    },
    {
      method: "fs.rm",
      params: {
        path: "app/env"
      }
    },
    {
      method: "fs.rm",
      params: {
        path: "app/sglang-omni"
      }
    },
    {
      method: "fs.rm",
      params: {
        path: "app/models"
      }
    }
  ]
}
