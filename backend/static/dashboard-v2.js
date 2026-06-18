const pageMeta = {
  home: ["Главная", "Коммерческая панель управления клиентами и контентом"],
  clients: ["Клиенты", "CRM и управление клиентами"],
  strategies: ["Стратегии", "Контент-стратегии клиентов"],
  plans: ["Контент-планы", "Календарь и планы публикаций"],
  channels: ["Каналы", "Аккаунты и интеграции клиентов"],
  youtube: ["YouTube", "Управление YouTube-каналами"],
  users: ["Пользователи", "Роли и доступы"],
  audit: ["Аудит", "Журнал действий"],
  settings: ["Настройки", "Tenant, безопасность и интеграции"]
};

function token(){
  return localStorage.getItem("ivadi_token");
}

async function authCheck(){
  const t = token();
  if(!t){
    window.location.href = "/login.html";
    return;
  }

  const res = await fetch("/api/auth/me", {
    headers:{Authorization:"Bearer " + t}
  });

  if(!res.ok){
    localStorage.removeItem("ivadi_token");
    localStorage.removeItem("ivadi_user");
    window.location.href = "/login.html";
    return;
  }

  const user = await res.json();
  window.IVADI_USER = user;
  document.getElementById("currentUser").innerHTML =
    `<b>${user.email}</b><br>${user.role}`;
}

async function api(path, options = {}){
  const headers = options.headers || {};
  headers.Authorization = "Bearer " + token();

  if(options.body && !headers["Content-Type"]){
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, {...options, headers});

  if(!res.ok){
    const data = await res.json().catch(()=>({}));
    throw new Error(data.detail || "Ошибка запроса");
  }

  return await res.json();
}

function showPage(name){
  document.querySelectorAll(".nav-item").forEach(x => x.classList.remove("active"));
  document.querySelectorAll(".page").forEach(x => x.classList.remove("active"));

  document.querySelector(`.nav-item[data-page="${name}"]`)?.classList.add("active");
  document.querySelector(`.page[data-page="${name}"]`)?.classList.add("active");

  const meta = pageMeta[name] || [name, ""];
  document.getElementById("pageTitle").textContent = meta[0];
  document.getElementById("pageSubtitle").textContent = meta[1];

  if(name === "users") loadUsers();
  if(name === "clients") loadClients();
}

async function loadUsers(){
  const box = document.getElementById("usersList");
  if(!box) return;
  box.textContent = "Загрузка...";

  try{
    const users = await api("/api/admin/users");

    if(!users.length){
      box.textContent = "Пользователей пока нет";
      return;
    }

    box.innerHTML = users.map(u => `
      <div class="row">
        <div>
          <div class="row-title">${u.email}</div>
          <div class="row-meta">role: ${u.role} · tenant: ${u.tenant_id ?? "-"} · client: ${u.client_id ?? "-"}</div>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <span class="badge ${u.is_active ? "active" : "disabled"}">${u.is_active ? "ACTIVE" : "OFF"}</span>
          <button class="danger" onclick="deactivateUser(${u.id})">Отключить</button>
        </div>
      </div>
    `).join("");
  }catch(e){
    box.innerHTML = `<span style="color:#fca5a5">${e.message}</span>`;
  }
}

async function createUser(){
  try{
    const clientId = document.getElementById("userClientId").value.trim();

    await api("/api/admin/users", {
      method:"POST",
      body:JSON.stringify({
        email:document.getElementById("userEmail").value.trim(),
        password:document.getElementById("userPassword").value,
        role:document.getElementById("userRole").value,
        client_id:clientId ? Number(clientId) : null,
        first_name:document.getElementById("userFirstName").value.trim() || null,
        last_name:document.getElementById("userLastName").value.trim() || null
      })
    });

    ["userEmail","userPassword","userClientId","userFirstName","userLastName"].forEach(id => {
      document.getElementById(id).value = "";
    });

    await loadUsers();
    alert("Пользователь создан");
  }catch(e){
    alert(e.message);
  }
}

async function deactivateUser(id){
  if(!confirm("Отключить пользователя?")) return;

  try{
    await api("/api/admin/users/" + id, {method:"DELETE"});
    await loadUsers();
  }catch(e){
    alert(e.message);
  }
}

async function loadClients(){
  const box = document.getElementById("clientsList");
  if(!box) return;
  box.textContent = "Загрузка...";

  try{
    const clients = await api("/api/clients");

    if(!clients.length){
      box.textContent = "Клиентов пока нет";
      return;
    }

    box.innerHTML = clients.map(c => `
      <div class="row">
        <div>
          <div class="row-title">${c.name || "Без названия"}</div>
          <div class="row-meta">brand: ${c.brand || "-"} · niche: ${c.niche || "-"} · status: ${c.status || "-"}</div>
        </div>
        <button class="primary small" onclick="alert('Карточка клиента будет следующим блоком')">Открыть</button>
      </div>
    `).join("");
  }catch(e){
    box.innerHTML = `<span style="color:#fca5a5">${e.message}</span>`;
  }
}

async function createClient(){
  try{
    await api("/api/clients", {
      method:"POST",
      body:JSON.stringify({
        name:document.getElementById("clientName").value.trim(),
        brand:document.getElementById("clientBrand").value.trim() || null,
        niche:document.getElementById("clientNiche").value.trim() || null,
        status:"active"
      })
    });

    ["clientName","clientBrand","clientNiche"].forEach(id => {
      document.getElementById(id).value = "";
    });

    await loadClients();
    alert("Клиент создан");
  }catch(e){
    alert(e.message);
  }
}

function logout(){
  localStorage.removeItem("ivadi_token");
  localStorage.removeItem("ivadi_user");
  window.location.href = "/login.html";
}

document.querySelectorAll(".nav-item[data-page]").forEach(btn => {
  btn.addEventListener("click", () => showPage(btn.dataset.page));
});

authCheck();
