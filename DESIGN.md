---
name: MoneyPrinterTurbo
description: A quiet editing workbench for local video production.
colors:
  accent: "#265c42"
  canvas: "#f4f4ee"
  surface: "#ffffff"
  ink: "#252a25"
  muted: "#5b635c"
  line: "#d8ded6"
  control-line: "#858e85"
  soft: "#edf4ee"
  danger: "#a12c26"
  error-bg: "#fff2ef"
  dark-accent: "#a2d4b4"
  dark-canvas: "#171e1a"
  dark-surface: "#202923"
  dark-ink: "#e5eae3"
  dark-muted: "#aebbad"
  dark-line: "#414c43"
  dark-control-line: "#859488"
  dark-soft: "#2a3c30"
  dark-danger: "#ffb3a5"
  dark-error-bg: "#432b27"
typography:
  headline:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "27px"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "18px"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.015em"
  title-small:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "16px"
    fontWeight: 650
  body:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "14px"
    lineHeight: 1.5
  label:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "12px"
    fontWeight: 600
  script:
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    fontSize: "15px"
    lineHeight: 1.8
    letterSpacing: "0.005em"
rounded:
  status: "3px"
  field: "4px"
  button: "5px"
spacing:
  compact: "4px"
  inline: "8px"
  small: "12px"
  divider: "14px"
  field: "18px"
  group: "20px"
  panel: "25px"
  heading: "28px"
  rail: "32px"
  workspace: "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.button}"
    padding: "7px 13px"
    height: "36px"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "7px 13px"
    height: "36px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.button}"
    padding: "6px 9px"
    height: "36px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "9px 11px"
  navigation-current:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.button}"
    padding: "7px 13px"
  status:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.accent}"
    rounded: "{rounded.status}"
    padding: "3px 7px"
  working-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "25px 30px"
---

# Design System: MoneyPrinterTurbo

## Overview

**Creative North Star: "Editing Workbench"**

MoneyPrinterTurbo uses a calm, compact visual language for sustained production work. Warm neutral surroundings separate the white working surfaces from the controls and output. A restrained forest-green accent identifies actions, selection and progress.

The system favors native browser controls, system UI typography and flat surfaces because it runs locally on PCs and Raspberry Pi installations. These choices are intentional. The product name and small geometric SVG brand mark remain visible; content and media are the working material.

**Key Characteristics:**

- Warm neutral canvas with clear working surfaces.
- A single green accent for actions and selected state.
- Compact, labeled native controls and system UI typography.
- Flat depth, light separators and restrained corners.
- Equivalent hierarchy in light, dark and system themes.

## Colors

The palette pairs warm, slightly green neutrals with forest-green action color; the frontmatter holds the normative values.

### Primary

- **Forest Green** (`accent`): primary actions, links, selected navigation, checkbox accents, progress and keyboard focus.
- **Pale Forest** (`dark-accent`): the corresponding accent in dark mode.
- **Quiet Green Wash** (`soft`, `dark-soft`): selected navigation, status labels and informational notices.

### Neutral

- **Warm Canvas** (`canvas`, `dark-canvas`): surrounding workspace and log backgrounds.
- **Working Surface** (`surface`, `dark-surface`): editors, settings panels, controls and app bar.
- **Charcoal Ink** (`ink`, `dark-ink`): main text.
- **Muted Leaf** (`muted`, `dark-muted`): help text, secondary actions and supporting metadata.
- **Quiet Separator** (`line`, `dark-line`): structural rules, row dividers and empty preview boundaries.
- **Control Boundary** (`control-line`, `dark-control-line`): native text fields and selects. Keep this stronger than structural separators.

Error text uses `danger` / `dark-danger` on `error-bg` / `dark-error-bg`. This is a semantic error pair, not an additional brand accent. Dark mode swaps the full semantic palette; system mode follows the device preference.

**The Control Boundary Rule.** Field outlines use the control-boundary color; layout dividers use the quieter separator color.

## Typography

**Body and heading font:** the system UI stack recorded in the frontmatter. There is no separate display face and no downloaded font dependency.

The hierarchy is compact and practical. Weight and spacing distinguish sections without introducing promotional typography. Body paragraphs have a maximum width of 70 characters where applicable.

### Hierarchy

- **Headline:** workspace headings; reduced to 24px below the mobile breakpoint.
- **Title:** section headings; the output heading uses a compact 15px variant.
- **Small title:** smaller content headings.
- **Body:** default interface copy; supporting descriptions often use 13px.
- **Label:** field labels, helpers and compact actions; field labels use the recorded semibold weight.
- **Script:** the large writing field; reduced to 14px on mobile.
- **Micro text:** status and file captions use 11px; logs use 11px with a 1.6 line-height.

**The Local Type Rule.** Use the system stack and the existing compact hierarchy for operational screens.

## Layout

The studio uses three columns at wide desktop sizes: a 174px stage rail, a flexible editor with a 350px minimum, and an output column ranging from 285px to 360px. The total layout is centered with a 1720px maximum. The app bar is at least 76px high; the editor has 36px top and 40px horizontal padding. These measurements describe the studio, not a required composition for every future surface.

At 1160px and below, the rail and output narrow to 145px and 290px and the editor padding reduces. At 960px and below, the output moves below the editor in the second column, the app navigation wraps onto its own row, and the empty preview changes from a portrait 9:12 ratio to 16:9. At 600px and below, the layout becomes a single flow: stages wrap horizontally, then the editor, then output. Editor and output use 20px horizontal padding.

The generation summary and primary action share a footer. It is sticky at the bottom on larger screens and uses normal document flow on mobile so it cannot cover the form.

Fields have a 7px label gap and 18px bottom margin. Paired fields use two equal columns with a 20px gap, reducing to 12px on mobile; settings fields collapse to one column on mobile. Settings, history and help use centered workspaces, section rules and grouped fields. Settings section navigation is sticky on larger screens and wraps horizontally on mobile.

Provider settings are organized by purpose: script, video/images, narration, transcription/subtitles, music and publishing. Keep each provider selector beside its credentials, state explicitly when an account key is shared, and preserve technical fields under Advanced. Editor stages link directly to the relevant category; category changes never save implicitly.

## Elevation & Depth

The interface has no shadow vocabulary. Surface color, spacing and one-pixel rules establish depth. The editor is bounded by quiet vertical rules; settings have a white working panel. Expandable advanced groups and history entries use horizontal rules rather than a card around each field.

**The Flat Workbench Rule.** Establish grouping with surface tone, spacing and separators.

## Shapes

Controls have gently restrained corners: buttons use the button radius, fields and working surfaces use the field radius, and statuses use the smaller status radius. Stage numbers are circular, with a one-pixel boundary and tabular numerals. Upload zones and empty preview frames use dashed separators. The only authored illustration is the small geometric SVG brand mark; native media and user content provide the larger visuals.

## Components

### Buttons

Compact, text-labeled actions use a minimum height of 36px, semibold weight and an 8px internal gap. Primary actions use the accent with working-surface text; secondary actions use the working surface with a quiet boundary. Quiet actions are transparent with muted text.

Secondary hover uses the green wash and accent boundary. Primary hover darkens with a brightness filter of 0.92. Keyboard focus is a 3px accent outline with a 3px offset. Disabled controls use 0.55 opacity and a disabled cursor. The studio generation button has a 43px minimum height.

### Inputs / Fields

Native input, select and textarea controls fill their column, use the control-boundary outline and retain visible labels. Hover changes the outline to muted text color; keyboard focus uses the shared focus treatment. Text areas resize vertically. The writing area is at least 285px high on desktop and 245px on mobile, with 18px internal padding.

Checkboxes retain the native control with accent coloring. Color fields pair a native color picker with a readable textual value. Notices describe errors outside the field; do not invent a field error border that the implementation does not have.

### Navigation

App navigation uses muted text on transparent buttons; selected items use the green wash and accent text. Stage navigation adds circular step numbers; the selected step uses an accent-filled number and a working-surface background. Settings navigation follows the same selected treatment. Text labels remain visible when navigation wraps.

Stage selection has a brief 140ms ease-out scale confirmation only when reduced motion is not requested. There is no general transition or decorative animation system.

### Status labels and notices

Status labels are compact rectangular tags with the green wash; failed status uses the error palette. They always contain text. Informational notices use the same soft surface and modest padding; error notices use the error pair and alert semantics.

### Working surfaces

The settings panel uses the recorded working-surface primitive. Login and startup panels are compact working surfaces with the button radius. History is a divided list. These are functional containers without shadows.

### Output monitor

Output remains a separate section while stages change. Empty output is a dashed, labeled frame. Active work uses native progress and expandable logs; finished work uses native video controls and explicit text actions. Audio auditions use native players. Media clips have restrained field-radius corners.

## Do's and Don'ts

### Do:

- **Do** keep visible field labels, text actions and the shared keyboard focus outline.
- **Do** use the full semantic palette when adding light and dark states.
- **Do** distinguish control boundaries from quieter structural separators.
- **Do** keep native controls and players for operational tasks.
- **Do** preserve responsive reading order and keep mobile actions in document flow.
- **Do** use flat working surfaces and section rules for dense configuration.

### Don't:

- **Don't** add a downloaded display font to operational screens without a new approved direction.
- **Don't** replace labeled actions or the geometric brand mark with decorative glyph icons.
- **Don't** use a card or shadow around every field.
- **Don't** use status color as the only status signal.
- **Don't** turn the studio's three-column composition into a universal layout requirement.
