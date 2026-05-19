import { useEffect, useRef, useState } from 'react';
import { Stage, Layer, Image as KImage, Line, Circle, Text, Group } from 'react-konva';
import type { Wall, AP, Material } from '../api/client';

const MATERIAL_COLORS: Record<Material, string> = {
  concrete: '#000000',
  brick:    '#8B4513',
  glass:    '#00CED1',
  wood:     '#D2691E',
  drywall:  '#A9A9A9',
  metal:    '#4B4B4B',
  door:     '#00B050',
};

interface Props {
  imageUrl: string | null;
  buildingW: number;
  buildingH: number;
  walls: Wall[];
  aps: AP[];
  showWalls?: boolean;       // toggle wall overlay visibility
}

export default function FloorPlanCanvas(
  { imageUrl, buildingW, buildingH, walls, aps, showWalls = true }: Props,
) {
  // Load image via plain HTMLImageElement (no extra dep)
  const [img, setImg] = useState<HTMLImageElement | null>(null);
  useEffect(() => {
    if (!imageUrl) { setImg(null); return; }
    const el = new window.Image();
    el.crossOrigin = 'anonymous';
    el.src = imageUrl;
    el.onload = () => setImg(el);
  }, [imageUrl]);

  // Fit canvas to parent
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [stageW, setStageW] = useState(800);
  const [stageH, setStageH] = useState(500);

  useEffect(() => {
    function onResize() {
      // Keep stage size STRICTLY proportional to building aspect.
      // Never clamp stageH to a minimum, or walls (which use the unclamped
      // scale) will not align with the image (which is stretched to stageH).
      const parentW = Math.max(300,
        (wrapperRef.current?.clientWidth ?? 800));
      const aspect = buildingW > 0 && buildingH > 0
        ? buildingH / buildingW : 0.6;
      // If the proportional height is too small for a wide building, grow
      // canvas DOWN by limiting width instead, so both image and walls
      // share the SAME scale.
      const maxH = 700;
      let w = parentW;
      let h = w * aspect;
      if (h > maxH) {
        h = maxH;
        w = h / aspect;
      }
      setStageW(w);
      setStageH(h);
    }
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [buildingW, buildingH]);

  // World (meters) -> stage px (SAME scale in both axes)
  const scale = buildingW > 0 ? stageW / buildingW : 1;
  const toPx = (v: number) => v * scale;

  return (
    <div ref={wrapperRef} className="w-full">
      <Stage width={stageW} height={stageH} className="border bg-white block">
        <Layer listening={false}>
          {img && (
            <KImage image={img} width={stageW} height={stageH} opacity={0.55} />
          )}
        </Layer>

        {showWalls && (
          <Layer listening={false}>
            {walls.map((w) => {
              const color = MATERIAL_COLORS[w.material];
              const x1 = toPx(w.p1_x), y1 = toPx(w.p1_y);
              const x2 = toPx(w.p2_x), y2 = toPx(w.p2_y);
              return (
                <Group key={w.id}>
                  {/* Soft outer glow so the detected line stands out
                       against the dark image walls */}
                  <Line
                    points={[x1, y1, x2, y2]}
                    stroke="#FFFFFF"
                    strokeWidth={4}
                    opacity={0.85}
                    lineCap="round"
                  />
                  {/* Main coloured line */}
                  <Line
                    points={[x1, y1, x2, y2]}
                    stroke={color}
                    strokeWidth={2}
                    opacity={0.95}
                    lineCap="round"
                  />
                  {/* End-point dots so users see EXACTLY where the
                       segment was detected */}
                  <Circle x={x1} y={y1} radius={3}
                          fill={color} stroke="white" strokeWidth={1} />
                  <Circle x={x2} y={y2} radius={3}
                          fill={color} stroke="white" strokeWidth={1} />
                </Group>
              );
            })}
          </Layer>
        )}

        <Layer>
          {aps.map((ap) => (
            <Group key={ap.id}>
              <Circle
                x={toPx(ap.x)} y={toPx(ap.y)}
                radius={8} fill="#dc2626" stroke="white" strokeWidth={2}
              />
              <Text
                x={toPx(ap.x) + 10}
                y={toPx(ap.y) - 6}
                text={ap.name}
                fontSize={11}
                fontStyle="bold"
                fill="#111"
              />
            </Group>
          ))}
        </Layer>
      </Stage>
    </div>
  );
}
