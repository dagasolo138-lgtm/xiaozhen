import { MouseEvent, useEffect, useRef, useState } from 'react';
import { HexCell } from '../api/client';
import { useWorldStore } from '../store/worldStore';

const terrain: Record<string, string> = {
  PLAIN: '#547d40',
  FOREST: '#245c35',
  MOUNTAIN: '#777',
  RIVER: '#2b7bba',
  COAST: '#41a6c7',
  DESERT: '#b89b52',
};

const HEX_SIZE = 5;
const CANVAS_WIDTH = 1100;
const CANVAS_HEIGHT = 640;

function hexCenter(cell: Pick<HexCell, 'q' | 'r'>) {
  return {
    x: cell.q * HEX_SIZE * 1.55 + (cell.r % 2 ? HEX_SIZE * 0.8 : 0) + 10,
    y: cell.r * HEX_SIZE * 1.34 + 10,
  };
}

function hexCorners(cx: number, cy: number) {
  return Array.from({ length: 6 }, (_, i) => {
    const angle = (Math.PI / 3) * i;
    return { x: cx + HEX_SIZE * Math.cos(angle), y: cy + HEX_SIZE * Math.sin(angle) };
  });
}

function containsPoint(cell: HexCell, x: number, y: number) {
  const center = hexCenter(cell);
  const corners = hexCorners(center.x, center.y);
  let inside = false;
  for (let i = 0, j = corners.length - 1; i < corners.length; j = i++) {
    const a = corners[i];
    const b = corners[j];
    const intersects = a.y > y !== b.y > y && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x;
    if (intersects) inside = !inside;
  }
  return inside;
}

function drawHex(ctx: CanvasRenderingContext2D, cell: HexCell) {
  const center = hexCenter(cell);
  const corners = hexCorners(center.x, center.y);
  ctx.fillStyle = terrain[cell.terrain] || '#555';
  ctx.beginPath();
  corners.forEach((corner, index) => (index ? ctx.lineTo(corner.x, corner.y) : ctx.moveTo(corner.x, corner.y)));
  ctx.closePath();
  ctx.fill();
  if (cell.nation_id) {
    ctx.globalAlpha = 0.25;
    ctx.fillStyle = '#fff';
    ctx.fill();
    ctx.globalAlpha = 1;
  }
}

export default function HexMap() {
  const ref = useRef<HTMLCanvasElement>(null);
  const { cells, selectedHex, setHex } = useWorldStore();
  const [drawMs, setDrawMs] = useState(0);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const started = performance.now();
    canvas.width = CANVAS_WIDTH;
    canvas.height = CANVAS_HEIGHT;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const cell of cells) drawHex(ctx, cell);
    if (selectedHex) {
      const selected = cells.find(cell => cell.id === selectedHex);
      if (selected) {
        const center = hexCenter(selected);
        ctx.strokeStyle = '#ffd166';
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (const [index, corner] of hexCorners(center.x, center.y).entries()) index ? ctx.lineTo(corner.x, corner.y) : ctx.moveTo(corner.x, corner.y);
        ctx.closePath();
        ctx.stroke();
      }
    }
    setDrawMs(performance.now() - started);
  }, [cells, selectedHex]);

  const onClick = (event: MouseEvent<HTMLCanvasElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) * (CANVAS_WIDTH / rect.width);
    const y = (event.clientY - rect.top) * (CANVAS_HEIGHT / rect.height);
    const cell = cells.find((candidate) => containsPoint(candidate, x, y));
    if (cell) setHex(cell.id);
  };

  return <div><canvas ref={ref} onClick={onClick} /><div className="mapStats">绘制耗时：{drawMs.toFixed(2)}ms {selectedHex ? `｜选中 ${selectedHex}` : ''}</div></div>;
}
