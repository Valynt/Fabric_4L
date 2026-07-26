import re

with open("apps/web/src/accessibility.a11y.spec.tsx", "r") as f:
    content = f.read()

content = content.replace('    const { container } = render(', '    const { container } = render(')

# Actually, vitest provides act. Let's just import act from "@testing-library/react" if not already there, and wrap the render calls.
import_pattern = r'import \{ render, screen \} from "@testing-library/react";'
content = re.sub(import_pattern, 'import { act, render, screen } from "@testing-library/react";', content)

def replacer(match):
    return f'''    let container: HTMLElement;
    await act(async () => {{
      const result = render(
{match.group(1)}
      );
      container = result.container;
    }});'''

content = re.sub(r'    const \{ container \} = render\(\n([\s\S]*?      </div>\n    \);)', replacer, content)

with open("apps/web/src/accessibility.a11y.spec.tsx", "w") as f:
    f.write(content)
