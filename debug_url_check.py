from geo_research.collector import get_video_id_from_url, fetch_video_metadata, fetch_transcript

url = 'https://youtu.be/20pTTT8jcEw?si=Nci0I9FiXOMXuVCN'
print('video_id=', get_video_id_from_url(url))

try:
    md = fetch_video_metadata(url)
    print('metadata=', md)
except Exception as e:
    print('metadata_error=', type(e).__name__, e)

try:
    txt = fetch_transcript(url)
    print('transcript_len=', len(txt))
    print('transcript_sample=', txt[:200])
except Exception as e:
    print('transcript_error=', type(e).__name__, e)
