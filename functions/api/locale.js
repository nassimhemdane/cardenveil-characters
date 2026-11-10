/** Country is supplied by Cloudflare; no location is requested from the visitor. */
export function onRequestGet({request}) {
  const french = new Set(['FR','BE','CH','LU','MC','CA','HT','SN','CI','BJ','BF','BI','CM','CF','TD','KM','CG','CD','DJ','GA','GN','GQ','MG','ML','NE','RW','SC','TG','VU','RE','GP','MQ','GF','YT','NC','PF','PM','WF','MF','BL']);
  const country = request.cf?.country;
  return Response.json({language: country ? (french.has(country) ? 'fr' : 'en') : null}, {
    headers: {'Cache-Control':'private, no-store'}
  });
}
