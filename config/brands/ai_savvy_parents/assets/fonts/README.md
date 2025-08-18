# AI-Savvy Parents Brand Fonts

## Required Fonts

### Primary Font: Inter
- **Usage**: Headers, buttons, UI elements, high-impact content
- **Weights Needed**: Light (300), Regular (400), Medium (500), Bold (700)
- **Source**: Google Fonts - https://fonts.google.com/specimen/Inter
- **License**: Open Font License (free for commercial use)

### Secondary Font: Source Sans Pro  
- **Usage**: Body text, descriptions, longer content blocks
- **Weights Needed**: Regular (400), Semi-Bold (600)
- **Source**: Google Fonts - https://fonts.google.com/specimen/Source+Sans+Pro
- **License**: Open Font License (free for commercial use)

## Font Files Needed

### Inter Font Files:
- `Inter-Light.woff2` (300)
- `Inter-Regular.woff2` (400) 
- `Inter-Medium.woff2` (500)
- `Inter-Bold.woff2` (700)

### Source Sans Pro Font Files:
- `SourceSansPro-Regular.woff2` (400)
- `SourceSansPro-SemiBold.woff2` (600)

## Installation Instructions

### Method 1: Download from Google Fonts
1. Visit Google Fonts for each font family
2. Select required weights
3. Download font files
4. Convert to WOFF2 format if needed
5. Place files in this directory

### Method 2: Using Font CDN (for web use)
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700&family=Source+Sans+Pro:wght@400;600&display=swap');
```

### Method 3: System Fonts Fallback
If fonts are not available, the system will fall back to:
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
```

## Font Loading in PDF Generation

### CSS Implementation:
```css
@font-face {
    font-family: 'Inter';
    src: url('fonts/Inter-Regular.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
}

@font-face {
    font-family: 'Source Sans Pro';
    src: url('fonts/SourceSansPro-Regular.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
}
```

### Playwright Configuration:
Ensure fonts are loaded before PDF generation for consistent rendering across platforms.

## Typography Scale

- **H1**: 24pt Inter Bold - Main headlines
- **H2**: 18pt Inter Bold - Section headers  
- **H3**: 14pt Inter Medium - Subsections
- **H4**: 12pt Inter Medium - Content headers
- **Body**: 11pt Source Sans Pro Regular - Main text
- **Small**: 9pt Source Sans Pro Regular - Captions, footnotes

## Brand Compliance

### Font Usage Rules:
- **Headers**: Always use Inter family
- **Body Text**: Always use Source Sans Pro
- **UI Elements**: Inter Medium or Bold
- **Emphasis**: Source Sans Pro Semi-Bold for body emphasis
- **Never**: Mix fonts within the same text block
- **Fallbacks**: Ensure graceful degradation to system fonts

---
**Current Status**: Placeholder - awaiting font files
**Next Steps**: Download and add font files to this directory
**Testing**: Verify font loading in PDF generation pipeline
