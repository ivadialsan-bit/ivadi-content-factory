const pageMeta = {
  home: ["Главная", "Операционная панель SaaS"],
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
}

async function loadUsers(){
  const box = document.getElementById("usersList");
  box.textContent = "Загрузка...";

  try{
    const users = await api("/api/admin/users");

    if(!users.length){
      box.textContent = "Пользователей пока нет";
      return;
    }

    box.innerHTML = users.map(u => `
      <div class="user-row">
        <div>
          <div class="user-email">${u.email}</div>
          <div class="user-meta">
            role: ${u.role} · tenant: ${u.tenant_id ?? "-"} · client: ${u.client_id ?? "-"} · active: ${u.is_active}
          </div>
        </div>
        <button class="danger" onclick="deactivateUser(${u.id})">Отключить</button>
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

    document.getElementById("userEmail").value = "";
    document.getElementById("userPassword").value = "";
    document.getElementById("userClientId").value = "";
    document.getElementById("userFirstName").value = "";
    document.getElementById("userLastName").value = "";

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

function logout(){
  localStorage.removeItem("ivadi_token");
  localStorage.removeItem("ivadi_user");
  window.location.href = "/login.html";
}

document.querySelectorAll(".nav-item[data-page]").forEach(btn => {
  btn.addEventListener("click", () => showPage(btn.dataset.page));
});

authCheck();
