import sqlite3
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
TOKEN_BOT = "8777550385:AAGE2qY1IQj0jn2Db7S4JwUACThxtyO5Ydo"
SEU_CHAT_ID = "7300892684"
CHAVE_PIX = "+5538991077142"

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Tabela de usuários com saldo real
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                      (nome TEXT PRIMARY KEY, saldo REAL DEFAULT 0.0)''')
    cursor.execute('CREATE TABLE IF NOT EXISTS codigos (codigo TEXT PRIMARY KEY, usado INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index(): return render_template_string(GAME_HTML)

# Rota para ganhar dinheiro jogando
@app.route('/ganhar_dinheiro', methods=['POST'])
def ganhar_dinheiro():
    dados = request.json
    nome = dados.get('nome')
    valor_ganho = 0.05 # Ganha 5 centavos por onda vencida
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO usuarios (nome, saldo) VALUES (?, 0.0)", (nome,))
    cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE nome = ?", (valor_ganho, nome))
    cursor.execute("SELECT saldo FROM usuarios WHERE nome = ?", (nome,))
    novo_saldo = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify({"saldo": round(novo_saldo, 2)})

# Rota de Saque
@app.route('/solicitar_saque', methods=['POST'])
def solicitar_saque():
    dados = request.json
    nome = dados.get('nome')
    pix_destino = dados.get('pix_usuario')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT saldo FROM usuarios WHERE nome = ?", (nome,))
    res = cursor.fetchone()
    
    if res and res[0] >= 20.0:
        saldo_atual = res[0]
        # Zera o saldo após o pedido
        cursor.execute("UPDATE usuarios SET saldo = 0.0 WHERE nome = ?", (nome,))
        conn.commit()
        # Avisa o Marcelo no Telegram
        aviso = f"💸 **PEDIDO DE SAQUE!**\n👤 Jogador: {nome}\n💰 Valor: R$ {saldo_atual:.2f}\n🔑 Pix Destino: {pix_destino}"
        requests.post(f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage", json={"chat_id": SEU_CHAT_ID, "text": aviso})
        conn.close()
        return jsonify({"status": "ok", "msg": "Pedido enviado! Marcelo pagará em breve."})
    else:
        conn.close()
        return jsonify({"status": "erro", "msg": "Saldo insuficiente (Mínimo R$ 20,00)"})

# --- HTML COM INTERFACE DE SALDO E SAQUE ---
GAME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <script src="https://cdn.jsdelivr.net/npm/phaser@3.55.2/dist/phaser.min.js"></script>
    <style>
        body { margin: 0; background: #000; color: #fff; font-family: sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; }
        .screen { width: 360px; height: 620px; display: none; flex-direction: column; align-items: center; border: 4px solid #f1c40f; position: relative; background: #0a0a0a; }
        .btn { width: 240px; padding: 12px; margin: 8px; background: #f1c40f; border: none; font-weight: bold; border-radius: 10px; cursor: pointer; color: #000; }
        .wallet { background: #222; padding: 15px; border-radius: 10px; border: 1px solid #27ae60; width: 80%; text-align: center; margin-top: 20px; }
    </style>
</head>
<body>

    <div id="start-screen" class="screen" style="display:flex;">
        <h1 style="color:#f1c40f">RENATO SURVIVAL</h1>
        <div class="wallet">
            <span style="color:#27ae60; font-size: 12px;">MEU SALDO PARA SAQUE</span><br>
            <b style="font-size: 24px;">R$ <span id="meu-saldo">0.00</span></b>
        </div>
        <button class="btn" onclick="iniciarJogo()">JOGAR E GANHAR</button>
        <button class="btn" style="background:#27ae60; color:white" onclick="abrirSaque()">💰 SACAR (MÍN. R$ 20)</button>
        <button class="btn" style="background:#9b59b6; color:white" onclick="showScreen('loja-screen')">🛒 LOJA DE SKINS</button>
    </div>

    <div id="game-screen" class="screen"><div id="phaser-game"></div></div>

    <script>
    let playerNome = "";
    let saldoTotal = 0.0;
    let wave = 1;

    function showScreen(id) {
        document.querySelectorAll('.screen').forEach(s => s.style.display = 'none');
        document.getElementById(id).style.display = 'flex';
    }

    function iniciarJogo() {
        if(!playerNome) playerNome = prompt("Digite seu Nickname para salvar seus ganhos:");
        if(playerNome) { showScreen('game-screen'); startGame(); }
    }

    function abrirSaque() {
        if(saldoTotal < 20) {
            alert("Você precisa de pelo menos R$ 20,00. Continue jogando!");
        } else {
            let pix = prompt("Digite sua chave PIX para receber:");
            if(pix) {
                fetch('/solicitar_saque', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({nome: playerNome, pix_usuario: pix})
                }).then(r => r.json()).then(data => {
                    alert(data.msg);
                    location.reload();
                });
            }
        }
    }

    // LÓGICA DO PHASER COM DIFICULDADE
    function startGame() {
        const config = {
            type: Phaser.AUTO, width: 360, height: 600, parent: 'phaser-game',
            physics: { default: 'arcade' },
            scene: { create: function() {
                let scene = this;
                this.wave = 1;
                this.player = this.add.text(180, 500, '🧔', {fontSize: '50px'});
                this.physics.add.existing(this.player);
                
                // Texto de Nível
                this.infoTxt = this.add.text(10, 10, "ONDA: 1", {color: '#f1c40f'});

                this.spawnEnemies = () => {
                    // DIFICULDADE: A cada 10 ondas, os inimigos ficam mais rápidos e vêm em maior número
                    let dificuldade = Math.floor(this.wave / 10) + 1;
                    let velocidade = 100 + (this.wave * 5);
                    
                    for(let i=0; i < (2 + dificuldade); i++) {
                        let e = this.add.text(Math.random()*300, -50, '👾', {fontSize: '30px'});
                        this.physics.add.existing(e);
                        e.body.setVelocityY(velocidade);
                        
                        this.physics.add.overlap(this.player, e, () => {
                            alert("FIM DE JOGO! Onda alcançada: " + this.wave);
                            location.reload();
                        });
                    }
                    
                    this.wave++;
                    this.infoTxt.setText("ONDA: " + this.wave + " (Dificuldade x" + dificuldade + ")");
                    
                    // Avisar o servidor que o jogador venceu uma onda (Ganha centavos)
                    fetch('/ganhar_dinheiro', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({nome: playerNome})
                    }).then(r => r.json()).then(data => {
                        saldoTotal = data.saldo;
                        document.getElementById('meu-saldo').innerText = saldoTotal.toFixed(2);
                    });
                };

                this.time.addEvent({ delay: 3000, callback: this.spawnEnemies, loop: true });
            }}
        };
        new Phaser.Game(config);
    }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

