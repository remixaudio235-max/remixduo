/** Admin-only view hosted by the dedicated RemiX Duo Cloudflare Worker.
 * Staff must also pass Cloudflare Access policy (configured in dashboard)
 * and present the Worker admin bearer secret. Do not cache the secret.
 */
export const adminHTML = String.raw`<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RemiX Duo — Cloudflare License Center</title>
<style>
:root{font-family:system-ui,"Segoe UI",sans-serif;color-scheme:dark;background:#080e16;color:#e6f6ff}
*{box-sizing:border-box}body{margin:0;padding:24px;max-width:900px;margin-inline:auto}
h1{font-size:25px;margin:0 0 8px;color:#4ee6ec}p{color:#a8c4d4}
section{padding:22px;margin-top:18px;background:#111c2b;border:1px solid #2c485b;border-radius:14px}
label{display:block;margin:14px 0 6px;font-size:13px;color:#b4d8e7}
input{background:#0d1723;border:1px solid #46647a;padding:11px 12px;color:#fff;border-radius:8px;width:100%;min-width:0}
button{background:#047a84;border:1px solid #24bfc9;color:white;border-radius:8px;padding:11px 16px;margin-top:14px;cursor:pointer}
button:hover{background:#09959d}button.secondary{background:#1b3548}
pre{padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;background:#080f19;border-radius:8px}
.columns{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:660px){.columns{grid-template-columns:1fr}}
.note{font-size:12px}
</style>
</head>
<body>
<h1>RemiX Duo — License Center</h1>
<p>Quản lý key từ Cloudflare Worker + D1. Private signing key chỉ tồn tại trong Cloudflare Worker Secret; ứng dụng khách không thể cấp key.</p>
<section>
<label for="admin">Admin API token (chỉ lưu trong bộ nhớ trang hiện tại)</label>
<input id="admin" type="password" autocomplete="off" placeholder="Nhập token bảo mật quản trị">
<p class="note">Trang này không ghi token vào localStorage, cookie hoặc URL. Nên bảo vệ thêm bằng Cloudflare Access.</p>
</section>
<section>
<h2>Cấp license mới</h2>
<div class="columns">
<div><label for="order">Mã đơn hàng</label><input id="order" maxlength="128" placeholder="DUO-ORDER-0001"></div>
<div><label for="customer">Khách hàng / đại lý</label><input id="customer" maxlength="128"></div>
<div><label for="days">Thời hạn (ngày, 0 = vĩnh viễn)</label><input id="days" type="number" min="0" max="36500" value="365"></div>
<div><label for="seats">Số thiết bị (1–500)</label><input id="seats" type="number" min="1" max="500" value="1"></div>
</div>
<button id="issue">Cấp key trên Cloudflare</button>
<pre id="issued">Key chỉ hiện một lần tại đây sau khi cấp thành công.</pre>
</section>
<section>
<h2>Tra cứu / thu hồi</h2>
<label for="id">License ID (UUID)</label>
<input id="id" placeholder="UUID trong kết quả cấp license">
<button id="lookup" class="secondary">Tra cứu</button>
<button id="revoke" class="secondary">Thu hồi license</button>
<pre id="details">Chưa tra cứu</pre>
</section>
<script src="/admin/app.js" defer></script>
</body></html>`;
export const adminJS=String.raw`(()=>{
"use strict";
const $=id=>document.getElementById(id);
const show=(id, data)=>{$(id).textContent=JSON.stringify(data,null,2)};
async function call(path, method="GET", payload){
 const token=$("admin").value.trim();
 if(!token) throw new Error("Cần nhập Admin API token");
 const resp=await fetch(path,{
  method,
  headers:{"authorization":"Bearer "+token, ...(payload?{"content-type":"application/json"}:{})},
  body:payload?JSON.stringify(payload):undefined,
  cache:"no-store"
 });
 const body=await resp.json();
 if(!resp.ok||body.ok===false) throw Error(body.error||"HTTP "+resp.status);
 return body;
}
$("issue").addEventListener("click",async()=>{
 $("issued").textContent="Đang xử lý...";
 try{
  const body=await call("/v1/admin/issue","POST",{
   order_id:$("order").value.trim(),customer:$("customer").value.trim(),
   days:Number($("days").value),seats:Number($("seats").value)
  });
  show("issued",body);
  $("id").value=body.license_id||"";
 }catch(err){$("issued").textContent="Lỗi: "+err.message}
});
$("lookup").addEventListener("click",async()=>{
 try{show("details",await call("/v1/admin/status?id="+encodeURIComponent($("id").value)))}
 catch(err){$("details").textContent="Lỗi: "+err.message}
});
$("revoke").addEventListener("click",async()=>{
 if(!confirm("Thu hồi license này? Các lần xác thực tiếp theo bị chặn."))return;
 try{show("details",await call("/v1/admin/revoke","POST",{license_id:$("id").value.trim()}))}
 catch(err){$("details").textContent="Lỗi: "+err.message}
});
})();`
