import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';

const KIE_API_KEY = Deno.env.get('KIE_API_KEY') ?? '';
const VEO = 'https://api.kie.ai/api/v1/veo';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, content-type',
};

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });

  try {
    const { taskId } = await req.json();
    if (!taskId) throw new Error('taskId is required');

    const res = await fetch(`${VEO}/record-info?taskId=${taskId}`, {
      headers: { 'Authorization': `Bearer ${KIE_API_KEY}` },
    });
    const data = await res.json();

    if (data.code !== 200) throw new Error(`VEO status error: ${data.msg}`);

    const status = data.data?.status; // 0=processing, 1=done, 2/3=error
    const resultUrls = data.data?.resultUrls;

    if (status === 1) {
      const videoUrl = Array.isArray(resultUrls) ? resultUrls[0] : resultUrls;
      return new Response(JSON.stringify({ done: true, video_url: videoUrl }), {
        headers: { ...cors, 'Content-Type': 'application/json' },
      });
    }

    if (status === 2 || status === 3) {
      throw new Error('Video generation failed on VEO side');
    }

    // status 0 = still processing
    return new Response(JSON.stringify({ done: false }), {
      headers: { ...cors, 'Content-Type': 'application/json' },
    });

  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), {
      status: 500,
      headers: { ...cors, 'Content-Type': 'application/json' },
    });
  }
});
