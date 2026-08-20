{
  "app": {
    "name": "LinkMint",
    "type": "public_saas_utility_dashboard",
    "brand_attributes": [
      "fast",
      "trustworthy",
      "quietly-premium",
      "developer-friendly",
      "data-forward"
    ],
    "north_star_actions": [
      "shorten-url",
      "copy-short-link",
      "review-recent-links",
      "delete-link",
      "view-click-counts"
    ]
  },
  "visual_personality": {
    "style_fusion": {
      "layout": "Bento grid hero + utility dashboard table (Dub-style SaaS patterns)",
      "surface": "Soft paper + subtle borders (Swiss/International Typographic Style discipline)",
      "accent": "Ocean-teal micro-accents + sand warmth",
      "motion": "Crisp micro-interactions; minimal but present"
    },
    "do_not": [
      "No purple-forward branding",
      "No heavy gradients on reading areas",
      "No centered app container",
      "No glossy skeuomorphic shadows"
    ]
  },
  "design_tokens": {
    "fonts": {
      "heading": {
        "google_font": "Space Grotesk",
        "fallback": "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial"
      },
      "body": {
        "google_font": "Inter",
        "fallback": "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial"
      },
      "mono": {
        "google_font": "Azeret Mono",
        "fallback": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, Courier New"
      },
      "notes": "Use mono only for short codes + URLs; keep body highly readable."
    },
    "typography_scale_tailwind": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight",
      "h2": "text-base md:text-lg text-muted-foreground",
      "section_title": "text-xl sm:text-2xl font-semibold tracking-tight",
      "body": "text-sm sm:text-base",
      "small": "text-xs text-muted-foreground"
    },
    "radius": {
      "card": "rounded-xl",
      "button": "rounded-lg",
      "input": "rounded-lg",
      "pill": "rounded-full"
    },
    "shadows": {
      "card": "shadow-[0_1px_0_rgba(15,23,42,0.04),0_10px_30px_rgba(15,23,42,0.06)]",
      "hover": "hover:shadow-[0_1px_0_rgba(15,23,42,0.06),0_16px_40px_rgba(15,23,42,0.10)]",
      "focus_ring": "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    },
    "spacing": {
      "page_x": "px-4 sm:px-6 lg:px-8",
      "page_y": "py-8 sm:py-10",
      "section_gap": "space-y-6 sm:space-y-8",
      "card_padding": "p-4 sm:p-6",
      "dense_row": "py-2.5"
    },
    "color_system_hsl": {
      "notes": "Update /app/frontend/src/index.css :root tokens to match these HSL values. Keep cards white; use teal as accent; sand as warm neutral. Ensure AA contrast.",
      "light": {
        "background": "36 33% 98%",
        "foreground": "222 47% 11%",
        "card": "0 0% 100%",
        "card_foreground": "222 47% 11%",
        "popover": "0 0% 100%",
        "popover_foreground": "222 47% 11%",
        "primary": "186 72% 26%",
        "primary_foreground": "0 0% 98%",
        "secondary": "34 28% 92%",
        "secondary_foreground": "222 47% 11%",
        "muted": "36 20% 94%",
        "muted_foreground": "215 16% 40%",
        "accent": "186 45% 92%",
        "accent_foreground": "186 72% 18%",
        "destructive": "0 72% 52%",
        "destructive_foreground": "0 0% 98%",
        "border": "30 18% 86%",
        "input": "30 18% 86%",
        "ring": "186 72% 26%",
        "chart_1": "186 72% 26%",
        "chart_2": "205 70% 38%",
        "chart_3": "34 70% 52%",
        "chart_4": "160 55% 34%",
        "chart_5": "12 70% 52%"
      },
      "dark_optional": {
        "background": "222 47% 7%",
        "foreground": "0 0% 98%",
        "card": "222 47% 9%",
        "card_foreground": "0 0% 98%",
        "primary": "186 70% 45%",
        "primary_foreground": "222 47% 7%",
        "secondary": "222 20% 14%",
        "secondary_foreground": "0 0% 98%",
        "muted": "222 20% 14%",
        "muted_foreground": "215 20% 70%",
        "accent": "186 30% 16%",
        "accent_foreground": "0 0% 98%",
        "border": "222 18% 18%",
        "input": "222 18% 18%",
        "ring": "186 70% 45%"
      },
      "semantic": {
        "success": "142 71% 45%",
        "warning": "38 92% 50%",
        "info": "205 90% 45%",
        "neutral": "215 16% 40%"
      }
    },
    "background_treatments": {
      "rule": "Gradients only as decorative section backgrounds (<=20% viewport). Cards remain solid.",
      "hero_mesh": {
        "tailwind": "bg-[radial-gradient(1200px_circle_at_10%_10%,hsl(var(--accent))_0%,transparent_55%),radial-gradient(900px_circle_at_90%_30%,hsl(var(--secondary))_0%,transparent_55%)]",
        "noise_overlay_css": "Use a ::before overlay with low-opacity SVG feTurbulence (0.06–0.10 opacity)."
      }
    }
  },
  "layout": {
    "grid": {
      "max_width": "max-w-6xl",
      "container": "mx-auto",
      "main": "min-h-screen",
      "bento": "grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6",
      "bento_blocks": {
        "shorten_form": "lg:col-span-7",
        "stats": "lg:col-span-5",
        "recent_links": "lg:col-span-12"
      }
    },
    "page_structure": {
      "home": [
        "Top bar (brand + subtle status)",
        "Hero: URL shortening form + result card",
        "Bento: stats summary cards",
        "Recent links table/list",
        "Footer microcopy"
      ],
      "redirect": [
        "Minimal interstitial: spinner + destination domain preview",
        "Error state: expired/not found with CTA back home"
      ]
    }
  },
  "components": {
    "component_path": {
      "shadcn_primary": [
        "/app/frontend/src/components/ui/button.jsx",
        "/app/frontend/src/components/ui/input.jsx",
        "/app/frontend/src/components/ui/label.jsx",
        "/app/frontend/src/components/ui/card.jsx",
        "/app/frontend/src/components/ui/badge.jsx",
        "/app/frontend/src/components/ui/table.jsx",
        "/app/frontend/src/components/ui/tabs.jsx",
        "/app/frontend/src/components/ui/dialog.jsx",
        "/app/frontend/src/components/ui/tooltip.jsx",
        "/app/frontend/src/components/ui/sonner.jsx",
        "/app/frontend/src/components/ui/skeleton.jsx",
        "/app/frontend/src/components/ui/separator.jsx",
        "/app/frontend/src/components/ui/calendar.jsx",
        "/app/frontend/src/components/ui/popover.jsx",
        "/app/frontend/src/components/ui/dropdown-menu.jsx"
      ],
      "notes": "Use existing shadcn/ui primitives; do not use raw HTML dropdown/calendar/toast."
    },
    "home_page_blocks": {
      "top_bar": {
        "structure": "Left: brand mark + name; Right: small status pill (Redis cache: ok) + GitHub link",
        "classes": "sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        "data_testids": [
          "topbar-brand-link",
          "topbar-status-pill",
          "topbar-github-link"
        ]
      },
      "shorten_form_card": {
        "components": ["Card", "Input", "Button", "Tooltip", "Popover", "Calendar"],
        "fields": [
          {
            "name": "long_url",
            "label": "Paste a long URL",
            "placeholder": "https://…",
            "data-testid": "shorten-form-long-url-input"
          },
          {
            "name": "custom_alias",
            "label": "Custom alias (optional)",
            "placeholder": "my-campaign",
            "data-testid": "shorten-form-custom-alias-input"
          },
          {
            "name": "expiration",
            "label": "Expiration (optional)",
            "ui": "Button-triggered Popover + Calendar",
            "data-testid": "shorten-form-expiration-trigger"
          }
        ],
        "primary_cta": {
          "label": "Shorten",
          "variant": "default",
          "classes": "bg-primary text-primary-foreground hover:bg-primary/90",
          "data-testid": "shorten-form-submit-button"
        },
        "secondary_actions": [
          {
            "label": "Clear",
            "variant": "ghost",
            "data-testid": "shorten-form-clear-button"
          }
        ]
      },
      "result_card": {
        "behavior": "Appears with subtle slide+fade after successful shorten; includes copy button + open-in-new-tab.",
        "components": ["Card", "Button", "Badge", "Tooltip", "Sonner toast"],
        "data_testids": [
          "shorten-result-card",
          "shorten-result-short-url",
          "shorten-result-copy-button",
          "shorten-result-open-button"
        ],
        "microcopy": "Copied. Share it anywhere."
      },
      "stats_bento": {
        "cards": [
          {
            "title": "Total links",
            "value": "#",
            "icon": "lucide Link",
            "data-testid": "stats-total-links"
          },
          {
            "title": "Total clicks",
            "value": "#",
            "icon": "lucide MousePointerClick",
            "data-testid": "stats-total-clicks"
          },
          {
            "title": "Active (not expired)",
            "value": "#",
            "icon": "lucide Activity",
            "data-testid": "stats-active-links"
          }
        ],
        "layout": "grid grid-cols-1 sm:grid-cols-3 gap-4",
        "card_style": "border bg-card/90 backdrop-blur"
      },
      "recent_links_table": {
        "components": ["Table", "Badge", "Button", "DropdownMenu", "Dialog", "Tooltip"],
        "columns": [
          "Short",
          "Original",
          "Clicks",
          "Created",
          "Expiry",
          "Actions"
        ],
        "row_actions": [
          {
            "name": "copy",
            "data-testid": "links-row-copy-button"
          },
          {
            "name": "delete",
            "confirm": "AlertDialog",
            "data-testid": "links-row-delete-button"
          }
        ],
        "empty_state": {
          "title": "No links yet",
          "body": "Shorten your first URL above — it’ll show up here with click counts.",
          "cta": {
            "label": "Paste a URL",
            "data-testid": "links-empty-cta-button"
          }
        }
      }
    },
    "redirect_page": {
      "loading": {
        "components": ["Card", "Progress", "Skeleton"],
        "copy": "Resolving link…",
        "data_testids": ["redirect-loading", "redirect-destination-domain"]
      },
      "error": {
        "components": ["Alert", "Button"],
        "copy": "This link doesn’t exist or has expired.",
        "data_testids": ["redirect-error", "redirect-back-home-button"]
      }
    }
  },
  "motion_and_microinteractions": {
    "principles": [
      "Motion is functional: confirm actions, guide attention, reduce perceived latency.",
      "Keep durations short; prefer opacity/translate; avoid layout jank."
    ],
    "timings": {
      "fast": "120ms",
      "base": "180ms",
      "slow": "240ms"
    },
    "patterns": {
      "button": "hover: translateY(-1px) + shadow increase; active: scale(0.98)",
      "cards": "hover border tint to accent + subtle shadow",
      "result_card_enter": "animate-in fade-in-0 slide-in-from-bottom-2 duration-200",
      "table_row": "hover:bg-muted/60",
      "copy_toast": "Use sonner toast with concise message; auto-close 2.5s"
    },
    "reduced_motion": "Respect prefers-reduced-motion: disable entrance animations and parallax."
  },
  "data_viz": {
    "library": {
      "recommended": "recharts",
      "use_cases": ["clicks over time mini area chart", "top links bar chart"],
      "install": "npm i recharts",
      "notes": "Use chart colors from --chart-1..5 tokens; keep gridlines subtle (stroke: hsl(var(--border)))."
    },
    "empty_states": {
      "chart": "Show Skeleton + 'No click data yet' caption"
    }
  },
  "accessibility": {
    "requirements": [
      "WCAG AA contrast for text and interactive elements",
      "Visible focus states using ring token",
      "Buttons must have aria-label when icon-only",
      "Inputs must have associated Label",
      "Toast messages should be short and non-blocking"
    ]
  },
  "testing_attributes": {
    "rule": "All interactive and key informational elements must include data-testid in kebab-case describing role.",
    "examples": [
      "data-testid=\"shorten-form-submit-button\"",
      "data-testid=\"links-row-delete-button\"",
      "data-testid=\"stats-total-clicks\""
    ]
  },
  "images": {
    "image_urls": [
      {
        "category": "hero_background_optional",
        "description": "Optional decorative hero background image (use as low-opacity overlay; do not exceed 20% viewport impact).",
        "url": "https://images.unsplash.com/photo-1651488829517-95af02975dd5?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "hero_background_optional",
        "description": "Alternative subtle teal paper texture for hero backdrop.",
        "url": "https://images.unsplash.com/photo-1657215374010-786fefd1dbbc?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85"
      },
      {
        "category": "og_preview_optional",
        "description": "If you generate an OG image for shared links, use this as a soft abstract base.",
        "url": "https://images.unsplash.com/photo-1617957848811-9c07f14d7ba3?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85"
      }
    ]
  },
  "implementation_notes_for_main_agent": {
    "instructions_to_main_agent": [
      "Replace CRA default App.css styles; remove centered .App-header patterns. Keep layout left-aligned.",
      "Update /app/frontend/src/index.css :root HSL tokens to the provided palette; keep shadcn variable names unchanged.",
      "Use Space Grotesk for headings and Inter for body via Google Fonts import in index.html or CSS; keep mono for short codes.",
      "Home page should be a bento grid: form/result on left, stats on right (desktop), stack on mobile.",
      "Use shadcn Table for recent links; on mobile, switch to Card list (same data) for readability.",
      "Use sonner for copy/delete feedback; every button/input/link must include data-testid.",
      "Redirect page: minimal Card with Skeleton/Progress; show destination domain; then redirect. Provide error Alert with back CTA."
    ],
    "js_files_note": "All component examples and imports should be written for .jsx (not .tsx)."
  },
  "appendix_general_ui_ux_design_guidelines": "<General UI UX Design Guidelines>\n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
