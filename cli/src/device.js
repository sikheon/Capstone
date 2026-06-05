import os from "node:os";

export function collectDeviceInfo(suggestedId) {
  return {
    client_id: suggestedId,
    kind: "cli",
    os: os.type(),                     // "Linux" | "Windows_NT" | "Darwin"
    arch: os.arch(),
    hostname: os.hostname(),
    model_hw: `${os.platform()} ${os.release()}`,
    app_version: "flctl-0.1.0",
    metadata: {
      node: process.version,
      user: os.userInfo().username,
    },
  };
}
