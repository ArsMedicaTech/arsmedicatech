# Markdown Rendering in Messages

The Messages component now supports rendering markdown content in message text. This allows for rich text formatting including headers, lists, code blocks, links, and more.

## Implementation

### Dependencies
- `react-markdown`: A React component for rendering markdown content

### Usage
Message text is automatically rendered as markdown using the `ReactMarkdown` component:

```tsx
<div className="message-text">
  <ReactMarkdown>{msg.text}</ReactMarkdown>
</div>
```

### Supported Markdown Features

The following markdown features are supported and styled:

#### Headers
```markdown
# H1 Header
## H2 Header
### H3 Header
```

#### Text Formatting
```markdown
**Bold text**
*Italic text*
`inline code`
```

#### Lists
```markdown
- Unordered list item
- Another item

1. Ordered list item
2. Another item
```

#### Code Blocks
```markdown
```javascript
function example() {
  return "Hello World";
}
```
```

#### Blockquotes
```markdown
> This is a blockquote
> It can span multiple lines
```

#### Links
```markdown
[Link text](https://example.com)
```

### Styling

The markdown content is styled with CSS classes in `Messages.css`:

- Headers have appropriate font sizes and margins
- Code blocks have a light gray background and monospace font
- Blockquotes have a left border and gray text
- Links are styled in blue with hover effects
- Lists have proper indentation and spacing

### Example

Here's an example of a message with markdown content:

```markdown
**Important:** Please note the following:

1. Take with food
2. Avoid grapefruit juice
3. Monitor for side effects

> If you experience any issues, contact us immediately.

You can also check our [medication guide](https://example.com/guide) for more details.
```

This will render as:
- Bold "Important" text
- Numbered list with proper formatting
- Blockquote with left border
- Clickable link

### Security

The `react-markdown` library automatically sanitizes HTML content to prevent XSS attacks, making it safe to render user-generated markdown content. 