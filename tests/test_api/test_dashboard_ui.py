import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import order_matching.api

UI_JS = Path(order_matching.api.__file__).parent / "static" / "ui.js"
NODE = shutil.which("node")

# Minimal DOM stand-in: records every innerHTML/onclick write so the test can prove API data never reaches them.
HARNESS = r"""
import { readFileSync } from 'node:fs';

const input = JSON.parse(readFileSync(0, 'utf8'));
const htmlWrites = [];
const inlineHandlers = [];

class FakeElement {
  constructor(tag) {
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.listeners = {};
    this.className = '';
    this.title = '';
    this.colSpan = 1;
    this.text = '';
  }
  set innerHTML(value) { htmlWrites.push(String(value)); this.children = []; this.text = ''; }
  get innerHTML() { return ''; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  set innerText(value) { this.textContent = value; }
  get innerText() { return this.textContent; }
  set onclick(value) { inlineHandlers.push(String(value)); }
  setAttribute(name, value) { if (name.startsWith('on')) inlineHandlers.push(String(value)); }
  appendChild(child) { this.children.push(child); return child; }
  append(...children) { children.forEach(c => this.appendChild(c)); }
  replaceChildren(...children) { this.children = []; this.text = ''; this.append(...children); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  click() { (this.listeners.click || []).forEach(fn => fn({ type: 'click', target: this })); }
  findAll(tag) {
    return this.children.flatMap(c => [...(c.tagName === tag ? [c] : []), ...c.findAll(tag)]);
  }
}

const tbody = new FakeElement('tbody');
globalThis.document = {
  getElementById: id => (id === 'outstanding-orders-body' ? tbody : null),
  createElement: tag => new FakeElement(tag),
};

const source = readFileSync(input.uiPath, 'utf8');
const ui = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));

const cancelled = [];
ui.renderOutstandingOrders(input.orderBook, orderId => cancelled.push(orderId));

const rows = tbody.findAll('TR').map(tr => ({
  cells: tr.findAll('TD').map(td => ({ text: td.textContent, title: td.title })),
}));
tbody.findAll('BUTTON').forEach(button => button.click());

process.stdout.write(JSON.stringify({ htmlWrites, inlineHandlers, rows, cancelled }));
"""


def _render_outstanding_orders(order_book: dict[str, Any]) -> dict[str, Any]:
    assert NODE is not None
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", HARNESS],
        input=json.dumps({"uiPath": str(UI_JS), "orderBook": order_book}),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


@pytest.mark.skipif(NODE is None, reason="Node.js is required to run the dashboard JavaScript")
def test_outstanding_orders_render_hostile_identifiers_inertly() -> None:
    order_id = "audit'order\"<b>"
    trader_id = "<img src=x onerror=globalThis.__auditXss=1>"
    order = {
        "order_id": order_id,
        "trader_id": trader_id,
        "side": "BUY",
        "price": 0.1,
        "size": 1.0,
        "timestamp": "2099-01-01T00:00:00",
    }

    result = _render_outstanding_orders({"bids": {"0.1": [order]}, "offers": {}})

    assert not any(order_id in html or trader_id in html for html in result["htmlWrites"])
    assert result["inlineHandlers"] == []
    [row] = result["rows"]
    id_cell, side_cell, _, _, trader_cell, _ = row["cells"]
    assert id_cell == {"text": order_id[:10], "title": order_id}
    assert side_cell["text"] == "BUY"
    assert trader_cell == {"text": trader_id, "title": trader_id}
    assert result["cancelled"] == [order_id]


@pytest.mark.skipif(NODE is None, reason="Node.js is required to run the dashboard JavaScript")
def test_outstanding_orders_render_empty_state() -> None:
    result = _render_outstanding_orders({"bids": {}, "offers": {}})

    assert [cell["text"] for row in result["rows"] for cell in row["cells"]] == ["No outstanding orders"]
    assert result["cancelled"] == []
