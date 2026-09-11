# Codex Pets

A small collection of custom animated character sheets for the ChatGPT desktop app and compatible Codex terminals.

自定义 Codex 动态角色素材合集。每个角色包都保留可直接安装的精灵图、配置文件、动作预览和验证报告。

## Characters

| Character | Description | Format |
| --- | --- | --- |
| [紬文德斯 / Tsumugi Wenders](pets/tsumugi-wenders/) | Warm-blonde twin tails, green eyes, and a gentle, curious personality | v2, 8×11 |

## Install

Clone this repository, then copy the selected character package into Codex's required local directory:

```bash
git clone https://github.com/soralcf/codex-pets.git
mkdir -p ~/.codex/pets/tsumugi-wenders
cp codex-pets/pets/tsumugi-wenders/pet.json ~/.codex/pets/tsumugi-wenders/
cp codex-pets/pets/tsumugi-wenders/spritesheet.webp ~/.codex/pets/tsumugi-wenders/
```

Open **Settings → Pets**, select **Refresh**, and choose the installed character. Custom desktop character packages are local resources and do not automatically sync to ChatGPT web; see the [official Pets documentation](https://learn.chatgpt.com/docs/pets).

## Repository layout

```text
pets/<pet-id>/
  pet.json
  spritesheet.webp
  previews/
  qa/
```

## Notice

This repository contains unofficial fan-made character artwork for personal customization. Character names, designs, and related intellectual property belong to their respective rights holders. No ownership of the underlying character is claimed.
