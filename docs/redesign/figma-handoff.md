# Civic Atlas — editable Figma handoff

File: [Civic Atlas redesign](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU)

## Review links

| Deliverable | Editable Figma frame | Size |
|---|---|---|
| Authority workbench | [Command centre](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU?node-id=5-2) | 1440 × 1040 |
| Citizen report desktop | [Desktop report form](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU?node-id=5-3) | 960 × 960 |
| Citizen report mobile | [Mobile report form](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU?node-id=5-4) | 390 × 1280 |
| Incident, risk context and worker handoff | [Review states](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU?node-id=5-5) | 760 × 1240 |
| Button, Field and Badge specimens | [Linked component review](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU?node-id=3-50) | 1040 × 760 |
| Palette and type foundations | [Foundation specimens](https://www.figma.com/design/ASRUgEx5N4L0JGwxDQSUGU?node-id=2-48) | 1024 × 640 |

The four screens contain **154 editable text nodes and 26 linked component instances**. No complete UI reference was imported as a bitmap: the final screen frames have **zero image fills**. Maps are native editable schematic geometry and explicitly labeled illustrative; the running application retains its actual interactive map tiles. This file does not claim survey accuracy or a live Figma weather/incident connection.

The authority snapshot uses the exact supplied values **12 total / 8 awaiting review / 3 active / 2 resolved**, plus the supplied synthetic `CS-DEMO-0004`, `CS-DEMO-0001`, and `CS-DEMO-0002` records. No extra metrics or refreshed timestamps were invented. Agent copy states text-rule Civic Intelligence, numerical weighted disaster risk, and rule-based coordination with human approval. The incident review preserves the statement that the photo has not been analyzed; it does not imply three live language models.

Validation: all token variables have WEB code syntax and explicit scopes; none uses `ALL_SCOPES`. All 13 semantic color variables alias palette primitives. Six shared text styles use discovered Manrope and IBM Plex Mono fonts. Button/Field/Badge masters remain separate from review-frame instances. No credentials, bearer tokens, backend source, private records, publication, or third-party login were used.

Completed scope: editable foundations, three local component families, the selected authority workbench, citizen report desktop/mobile layouts, and representative authority incident/risk/worker review states. Composition follows the selected `atlas-workbench-concept.png` direction. This design file is a review artifact, not a deployed application or live operational feed.

Discovery completed: the new Design file was blank; no Code Connect mappings or existing product components were present. Library discovery found community kits, and a focused Simple Design System search found Button/Input assets. Those remote assets use a different visual/token system; the approved Civic Atlas Manrope/forest/paper direction therefore uses local components. Manrope and IBM Plex Mono exact font styles were discovered before text creation. No credentials, backend source, private records, or full UI screenshots were uploaded.

## Created foundations

- Two variable collections with 38 variables: primitive palette, aliased semantic colors, spacing, corner radii, stroke width, and font families.
- Explicit variable scopes and WEB `var(--...)` code syntax.
- Six shared text styles: Display, Heading, Section, Body, Label, Meta.
- Editable foundation specimen frame, plus component and screen pages.
- Design mode: one approved light palette. No extra theme was invented.

## State ledger

Run: `civic-atlas-20261017`. Last completed phase: `screens/visually-verified`. Foundations, components, and all four screen frames were inspected at normal scale. Badge labels, schematic zone opacity, desktop table clipping, and review-card truncation were repaired. The final affected screenshots passed inspection.

```json
{
  "createdNodeIds": [
    "2:48",
    "2:49",
    "2:50",
    "2:51",
    "2:52",
    "2:53",
    "2:54",
    "2:55",
    "2:56",
    "2:57",
    "2:58",
    "2:59",
    "2:60",
    "2:61",
    "2:62",
    "2:63",
    "2:64",
    "2:65",
    "2:66",
    "2:67",
    "2:68",
    "2:69",
    "2:70",
    "2:71",
    "2:72",
    "2:73",
    "2:74",
    "2:75",
    "2:76",
    "2:77",
    "2:78",
    "2:79"
  ],
  "mutatedNodeIds": [
    "0:1"
  ],
  "createdVariableIds": [
    "VariableID:2:4",
    "VariableID:2:5",
    "VariableID:2:6",
    "VariableID:2:7",
    "VariableID:2:8",
    "VariableID:2:9",
    "VariableID:2:10",
    "VariableID:2:11",
    "VariableID:2:12",
    "VariableID:2:13",
    "VariableID:2:14",
    "VariableID:2:15",
    "VariableID:2:16",
    "VariableID:2:17",
    "VariableID:2:18",
    "VariableID:2:19",
    "VariableID:2:20",
    "VariableID:2:21",
    "VariableID:2:22",
    "VariableID:2:23",
    "VariableID:2:24",
    "VariableID:2:25",
    "VariableID:2:26",
    "VariableID:2:27",
    "VariableID:2:28",
    "VariableID:2:29",
    "VariableID:2:30",
    "VariableID:2:31",
    "VariableID:2:32",
    "VariableID:2:33",
    "VariableID:2:34",
    "VariableID:2:35",
    "VariableID:2:36",
    "VariableID:2:37",
    "VariableID:2:38",
    "VariableID:2:39",
    "VariableID:2:40",
    "VariableID:2:41"
  ],
  "createdStyleIds": [
    "S:291b89fdf298971244e1e10d1f2f2f92a24d4ddd,",
    "S:aca7e95e692fa8a62e838fdd81efe7bd7b988fe9,",
    "S:5bee28c8f67c24c142bdfc3460a2ed9b4ef29208,",
    "S:ea998874631599f167fabf23fb49996a91c5caf5,",
    "S:9768c9fdaff5e42d7c65011ac85b6015bdd31479,",
    "S:1d3eed90ce3abc760bd642dfb14b389ef943a7f5,"
  ],
  "collectionIds": [
    "VariableCollectionId:2:2",
    "VariableCollectionId:2:3"
  ],
  "pages": {
    "foundations": "0:1",
    "components": "2:78",
    "screens": "2:79"
  },
  "variables": {
    "palette/paper": "VariableID:2:4",
    "palette/white": "VariableID:2:5",
    "palette/ink": "VariableID:2:6",
    "palette/muted": "VariableID:2:7",
    "palette/forest": "VariableID:2:8",
    "palette/warning": "VariableID:2:9",
    "palette/critical": "VariableID:2:10",
    "palette/positive": "VariableID:2:11",
    "palette/border": "VariableID:2:12",
    "palette/forestHover": "VariableID:2:13",
    "palette/tint": "VariableID:2:14",
    "color/bg": "VariableID:2:15",
    "color/surface": "VariableID:2:16",
    "color/nav": "VariableID:2:17",
    "color/text": "VariableID:2:18",
    "color/muted": "VariableID:2:19",
    "color/accent": "VariableID:2:20",
    "color/accent-hover": "VariableID:2:21",
    "color/on-accent": "VariableID:2:22",
    "color/warning": "VariableID:2:23",
    "color/critical": "VariableID:2:24",
    "color/positive": "VariableID:2:25",
    "color/border": "VariableID:2:26",
    "color/tint": "VariableID:2:27",
    "spacing/xs": "VariableID:2:28",
    "spacing/sm": "VariableID:2:29",
    "spacing/md": "VariableID:2:30",
    "spacing/lg": "VariableID:2:31",
    "spacing/xl": "VariableID:2:32",
    "spacing/xxl": "VariableID:2:33",
    "spacing/section": "VariableID:2:34",
    "radius/sm": "VariableID:2:35",
    "radius/md": "VariableID:2:36",
    "radius/lg": "VariableID:2:37",
    "radius/full": "VariableID:2:38",
    "stroke/default": "VariableID:2:39",
    "font/sans": "VariableID:2:40",
    "font/mono": "VariableID:2:41"
  },
  "styles": {
    "Display": "S:291b89fdf298971244e1e10d1f2f2f92a24d4ddd,",
    "Heading": "S:aca7e95e692fa8a62e838fdd81efe7bd7b988fe9,",
    "Section": "S:5bee28c8f67c24c142bdfc3460a2ed9b4ef29208,",
    "Body": "S:ea998874631599f167fabf23fb49996a91c5caf5,",
    "Label": "S:9768c9fdaff5e42d7c65011ac85b6015bdd31479,",
    "Meta": "S:1d3eed90ce3abc760bd642dfb14b389ef943a7f5,"
  },
  "foundationFrameId": "2:48",
  "tokenCount": 38
}
```

## Component phase

Three editable component families are available: Button (9 variants), Field (3 states), and Badge (4 tones). Labels and input values are exposed as editable text properties. Specimens use linked instances; main components are kept outside the review frame. Fills, strokes, padding, gaps, radii, and shared text styles are bound to the foundations. The final normal-scale review showed readable labels, complete field helpers, and no clipping.

```json
{
  "createdNodeIds": [
    "3:2",
    "3:3",
    "3:4",
    "3:5",
    "3:6",
    "3:7",
    "3:8",
    "3:9",
    "3:10",
    "3:11",
    "3:12",
    "3:13",
    "3:14",
    "3:15",
    "3:16",
    "3:17",
    "3:18",
    "3:19",
    "3:20",
    "3:21",
    "3:22",
    "3:23",
    "3:24",
    "3:25",
    "3:26",
    "3:27",
    "3:28",
    "3:29",
    "3:30",
    "3:31",
    "3:32",
    "3:33",
    "3:34",
    "3:35",
    "3:36",
    "3:37",
    "3:38",
    "3:39",
    "3:40",
    "3:41",
    "3:42",
    "3:43",
    "3:44",
    "3:45",
    "3:46",
    "3:47",
    "3:48",
    "3:49",
    "3:50",
    "3:51",
    "3:52",
    "3:53",
    "3:54",
    "3:55",
    "3:57",
    "3:59",
    "3:61",
    "3:63",
    "3:65",
    "3:66",
    "3:67",
    "3:72",
    "3:77",
    "3:82",
    "3:83",
    "3:84",
    "3:87",
    "3:90",
    "3:93",
    "3:96"
  ],
  "mutatedNodeIds": [],
  "sets": {
    "button": {
      "id": "3:11",
      "variants": [
        {
          "id": "3:2",
          "name": "Style=Primary, State=Default"
        },
        {
          "id": "3:3",
          "name": "Style=Primary, State=Hover"
        },
        {
          "id": "3:4",
          "name": "Style=Primary, State=Disabled"
        },
        {
          "id": "3:5",
          "name": "Style=Secondary, State=Default"
        },
        {
          "id": "3:6",
          "name": "Style=Secondary, State=Hover"
        },
        {
          "id": "3:7",
          "name": "Style=Secondary, State=Disabled"
        },
        {
          "id": "3:8",
          "name": "Style=Ghost, State=Default"
        },
        {
          "id": "3:9",
          "name": "Style=Ghost, State=Hover"
        },
        {
          "id": "3:10",
          "name": "Style=Ghost, State=Disabled"
        }
      ],
      "labelProperty": "Label#3:0"
    },
    "field": {
      "id": "3:24",
      "variants": [
        {
          "id": "3:21",
          "name": "State=Default"
        },
        {
          "id": "3:22",
          "name": "State=Focus"
        },
        {
          "id": "3:23",
          "name": "State=Error"
        }
      ],
      "labelProperty": "Label#3:10",
      "valueProperty": "Value#3:14"
    },
    "badge": {
      "id": "3:41",
      "variants": [
        {
          "id": "3:37",
          "name": "Tone=Neutral"
        },
        {
          "id": "3:38",
          "name": "Tone=High"
        },
        {
          "id": "3:39",
          "name": "Tone=Critical"
        },
        {
          "id": "3:40",
          "name": "Tone=Positive"
        }
      ],
      "labelProperty": "Label#3:18"
    }
  },
  "reviewFrameId": "3:50",
  "variantCount": 16,
  "bindings": {
    "sampleButton": {
      "itemSpacing": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:29"
      },
      "paddingLeft": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:30"
      },
      "paddingTop": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:30"
      },
      "paddingRight": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:30"
      },
      "paddingBottom": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:30"
      },
      "topLeftRadius": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:35"
      },
      "topRightRadius": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:35"
      },
      "bottomLeftRadius": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:35"
      },
      "bottomRightRadius": {
        "type": "VARIABLE_ALIAS",
        "id": "VariableID:2:35"
      },
      "fills": [
        {
          "type": "VARIABLE_ALIAS",
          "id": "VariableID:2:20"
        }
      ]
    },
    "sampleLabel": "S:9768c9fdaff5e42d7c65011ac85b6015bdd31479,"
  },
  "bounds": {
    "width": 1040,
    "height": 760
  }
}
```


## Screen phase state ledger

```json
{
  "phase": "screens/visually-verified",
  "selectedConcept": "docs/redesign/atlas-workbench-concept.png",
  "frames": {
    "authority": {
      "id": "5:2",
      "width": 1440,
      "height": 1040,
      "textCount": 70,
      "instanceCount": 4
    },
    "citizenDesktop": {
      "id": "5:3",
      "width": 960,
      "height": 960,
      "textCount": 28,
      "instanceCount": 7
    },
    "citizenMobile": {
      "id": "5:4",
      "width": 390,
      "height": 1280,
      "textCount": 25,
      "instanceCount": 6
    },
    "incidentRiskWorker": {
      "id": "5:5",
      "width": 760,
      "height": 1240,
      "textCount": 31,
      "instanceCount": 9
    }
  },
  "createdNodeIds": [
    "7:2",
    "7:3",
    "7:4",
    "7:5",
    "7:6",
    "7:7",
    "7:8",
    "7:9",
    "7:10",
    "7:11",
    "7:12",
    "7:13",
    "7:14",
    "7:15",
    "7:16",
    "7:17",
    "7:18",
    "7:19",
    "7:20",
    "7:21",
    "7:22",
    "7:23",
    "7:24",
    "7:25",
    "7:26",
    "7:27",
    "7:28",
    "7:29",
    "7:30",
    "7:31",
    "7:32",
    "7:33",
    "7:34",
    "7:35",
    "7:36",
    "7:37",
    "7:38",
    "7:39",
    "7:40",
    "I7:40;3:12",
    "7:42",
    "7:43",
    "7:44",
    "7:45",
    "7:46",
    "7:47",
    "7:48",
    "7:49",
    "7:50",
    "7:51",
    "7:52",
    "7:53",
    "7:54",
    "7:55",
    "7:56",
    "7:57",
    "7:58",
    "7:59",
    "7:60",
    "7:61",
    "7:62",
    "7:63",
    "7:64",
    "7:65",
    "7:66",
    "7:67",
    "7:68",
    "7:69",
    "7:70",
    "7:71",
    "7:72",
    "7:73",
    "7:74",
    "7:75",
    "7:76",
    "7:77",
    "7:78",
    "7:79",
    "7:80",
    "7:81",
    "7:82",
    "7:83",
    "7:84",
    "7:85",
    "7:86",
    "7:87",
    "7:88",
    "7:89",
    "7:90",
    "7:91",
    "7:92",
    "7:93",
    "7:94",
    "I7:94;3:46",
    "I7:94;3:47",
    "7:97",
    "7:98",
    "7:99",
    "7:100",
    "7:101",
    "7:102",
    "7:103",
    "7:104",
    "I7:104;3:44",
    "I7:104;3:45",
    "7:107",
    "7:108",
    "7:109",
    "7:110",
    "7:111",
    "7:112",
    "7:113",
    "7:114",
    "I7:114;3:44",
    "I7:114;3:45",
    "7:117",
    "7:118",
    "7:119",
    "7:120",
    "7:121",
    "7:122",
    "7:123",
    "7:124",
    "7:125",
    "7:126",
    "7:127",
    "7:128",
    "7:129",
    "7:130",
    "7:131",
    "7:132",
    "7:133",
    "7:134",
    "7:135",
    "7:136",
    "7:137",
    "7:138",
    "7:139",
    "7:140",
    "7:141",
    "7:142",
    "7:143",
    "7:144",
    "7:145",
    "7:146",
    "7:147",
    "7:148",
    "7:149",
    "7:150",
    "7:151",
    "7:152",
    "9:9",
    "9:10",
    "9:11",
    "9:12",
    "9:13",
    "9:14",
    "I9:14;3:25",
    "I9:14;3:26",
    "I9:14;3:27",
    "I9:14;3:28",
    "9:19",
    "I9:19;3:25",
    "I9:19;3:26",
    "I9:19;3:27",
    "I9:19;3:28",
    "9:24",
    "9:25",
    "9:26",
    "9:27",
    "9:28",
    "9:29",
    "9:30",
    "9:31",
    "9:32",
    "9:33",
    "9:34",
    "9:35",
    "9:36",
    "9:37",
    "9:38",
    "9:39",
    "9:40",
    "9:41",
    "I9:41;3:18",
    "9:43",
    "9:44",
    "9:45",
    "9:46",
    "9:47",
    "9:48",
    "9:49",
    "9:50",
    "9:51",
    "9:52",
    "9:53",
    "9:54",
    "9:55",
    "9:56",
    "9:57",
    "9:58",
    "9:59",
    "9:60",
    "9:61",
    "9:62",
    "I9:62;3:25",
    "I9:62;3:26",
    "I9:62;3:27",
    "I9:62;3:28",
    "9:67",
    "I9:67;3:25",
    "I9:67;3:26",
    "I9:67;3:27",
    "I9:67;3:28",
    "9:72",
    "9:73",
    "9:74",
    "9:75",
    "I9:75;3:15",
    "9:77",
    "I9:77;3:12",
    "9:79",
    "9:80",
    "9:81",
    "9:82",
    "9:83",
    "9:84",
    "9:85",
    "9:86",
    "9:87",
    "I9:87;3:25",
    "I9:87;3:26",
    "I9:87;3:27",
    "I9:87;3:28",
    "9:92",
    "I9:92;3:25",
    "I9:92;3:26",
    "I9:92;3:27",
    "I9:92;3:28",
    "9:97",
    "9:98",
    "9:99",
    "9:100",
    "9:101",
    "9:102",
    "9:103",
    "9:104",
    "9:105",
    "9:106",
    "9:107",
    "9:108",
    "9:109",
    "I9:109;3:18",
    "9:111",
    "9:112",
    "9:113",
    "9:114",
    "9:115",
    "9:116",
    "9:117",
    "9:118",
    "9:119",
    "9:120",
    "9:121",
    "9:122",
    "9:123",
    "9:124",
    "9:125",
    "9:126",
    "9:127",
    "9:128",
    "I9:128;3:25",
    "I9:128;3:26",
    "I9:128;3:27",
    "I9:128;3:28",
    "9:133",
    "I9:133;3:25",
    "I9:133;3:26",
    "I9:133;3:27",
    "I9:133;3:28",
    "9:138",
    "9:139",
    "9:140",
    "I9:140;3:12",
    "9:142",
    "10:46",
    "10:47",
    "10:48",
    "10:49",
    "10:50",
    "I10:50;3:44",
    "I10:50;3:45",
    "10:53",
    "I10:53;3:42",
    "I10:53;3:43",
    "10:56",
    "10:57",
    "10:58",
    "I10:58;3:15",
    "10:60",
    "I10:60;3:18",
    "10:62",
    "I10:62;3:18",
    "10:64",
    "I10:64;3:18",
    "10:66",
    "10:67",
    "10:68",
    "10:69",
    "10:70",
    "I10:70;3:18",
    "10:72",
    "10:73",
    "10:74",
    "10:75",
    "10:76",
    "10:77",
    "10:78",
    "10:79",
    "10:80",
    "10:81",
    "10:82",
    "10:83",
    "10:84",
    "10:85",
    "10:86",
    "10:87",
    "10:88",
    "10:89",
    "I10:89;3:42",
    "I10:89;3:43",
    "10:92",
    "10:93",
    "10:94",
    "10:95",
    "10:96",
    "10:97",
    "10:98",
    "10:99",
    "10:100",
    "I10:100;3:12",
    "10:102"
  ],
  "mutatedNodeIds": [
    "5:2",
    "5:3",
    "5:4",
    "5:5",
    "7:71",
    "7:73",
    "7:75",
    "7:77",
    "7:87",
    "7:136",
    "7:50",
    "10:46",
    "10:66",
    "10:75",
    "10:79",
    "10:85"
  ],
  "imageFillCount": 0,
  "validation": "Normal-scale screenshots reviewed for each screen. Table clipping and review-card truncation were repaired and the final affected screenshots passed."
}
```

