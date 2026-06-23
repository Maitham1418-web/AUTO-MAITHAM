import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

const KIE_API_KEY = Deno.env.get('KIE_API_KEY') ?? '';
const VEO = 'https://api.kie.ai/api/v1/veo';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type',
};

const MOTION: Record<string, string> = {
  promo_reel:    'dynamic product showcase, smooth cinematic camera movements, vibrant professional lighting, product always visible',
  product_story: 'elegant slow reveal of the product, cinematic dolly forward, soft warm lighting, product centered throughout',
  offer_discount:'exciting bold product highlight, energetic camera movement, eye-catching colors, product prominent in frame',
  brand_intro:   'luxurious product presentation, sophisticated camera orbit, premium brand atmosphere, product as hero',
};

function buildPrompt(userPrompt: string, adType: string, hasImage: boolean): string {
  const motion = MOTION[adType] ?? MOTION.promo_reel;
  if (hasImage) {
    return `Professional social media advertisement. ${motion}. ` +
           `Product shown in image: ${userPrompt}. ` +
           `Keep the product clearly visible and prominent throughout the entire video. ` +
           `High quality cinematic advertisement suitable for Instagram Reels and TikTok.`;
  }
  return `Create a professional social media advertisement video. ${motion}. ` +
         `Product: ${userPrompt}. ` +
         `High quality 4K cinematic, suitable for Instagram Reels and TikTok.`;
}

function mapAspectRatio(videoSize: string): string {
  if (videoSize === '16:9') return '16:9';
  if (videoSize === '9:16' || videoSize === '4:5' || videoSize === '1:1') return '9:16';
  return '9:16';
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });

  try {
    const { prompt, imageUrls, videoSize, adType } = await req.json();
    if (!prompt) throw new Error('prompt is required');

    const aspect_ratio = mapAspectRatio(videoSize ?? '9:16');
    const hasImage = Array.isArray(imageUrls) && imageUrls.length > 0 && !!imageUrls[0];
    const finalPrompt = buildPrompt(prompt, adType ?? 'promo_reel', hasImage);

    const body: Record<string, unknown> = {
      prompt: finalPrompt,
      model: 'veo3',
      aspect_ratio,
      resolution: '4k',
      duration: 8,
      watermark: '',
    };

    // إضافة الصورة لـ image-to-video
    if (hasImage && imageUrls[0].startsWith('https://')) {
      body.imageUrls = [imageUrls[0]];
    }

    const genRes = await fetch(`${VEO}/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${KIE_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const genData = await genRes.json();
    if (genData.code !== 200) throw new Error(`VEO error: ${genData.msg}`);

    // نرجع taskId فوراً — الـ polling يصير في المتصفح
    return new Response(JSON.stringify({ taskId: genData.data.taskId }), {
      headers: { ...cors, 'Content-Type': 'application/json' },
    });

  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), {
      status: 500,
      headers: { ...cors, 'Content-Type': 'application/json' },
    });
  }
});
