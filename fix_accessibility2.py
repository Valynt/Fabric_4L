import re

with open("apps/web/src/accessibility.a11y.spec.tsx", "r") as f:
    content = f.read()

import_pattern = r'import \{ render, screen \} from "@testing-library/react";'
content = re.sub(import_pattern, 'import { act, render, screen } from "@testing-library/react";', content)

# Instead of regex, let's just replace the exact problematic blocks

b1 = """  it("virtual list single-column passes axe", async () => {
    const { container } = render(
      <div style={{ height: "200px" }}>
        <VirtualList
          items={[
            { id: "1", label: "First" },
            { id: "2", label: "Second" },
            { id: "3", label: "Third" },
          ]}
          estimateSize={50}
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );"""

r1 = """  it("virtual list single-column passes axe", async () => {
    let container: HTMLElement | undefined;
    await act(async () => {
      const res = render(
        <div style={{ height: "200px" }}>
          <VirtualList
            items={[
              { id: "1", label: "First" },
              { id: "2", label: "Second" },
              { id: "3", label: "Third" },
            ]}
            estimateSize={50}
            renderItem={(item) => <div>{item.label}</div>}
          />
        </div>
      );
      container = res.container;
    });"""

b2 = """  it("virtual list multi-column grid passes axe", async () => {
    const { container } = render(
      <div style={{ height: "200px" }}>
        <VirtualList
          items={[
            { id: "1", label: "A" },
            { id: "2", label: "B" },
            { id: "3", label: "C" },
          ]}
          estimateSize={80}
          columns={3}
          renderItem={(item) => <div>{item.label}</div>}
        />
      </div>
    );"""

r2 = """  it("virtual list multi-column grid passes axe", async () => {
    let container: HTMLElement | undefined;
    await act(async () => {
      const res = render(
        <div style={{ height: "200px" }}>
          <VirtualList
            items={[
              { id: "1", label: "A" },
              { id: "2", label: "B" },
              { id: "3", label: "C" },
            ]}
            estimateSize={80}
            columns={3}
            renderItem={(item) => <div>{item.label}</div>}
          />
        </div>
      );
      container = res.container;
    });"""

content = content.replace(b1, r1)
content = content.replace(b2, r2)
content = content.replace('const results = await axe(container);', 'const results = await axe(container as HTMLElement);')

with open("apps/web/src/accessibility.a11y.spec.tsx", "w") as f:
    f.write(content)
