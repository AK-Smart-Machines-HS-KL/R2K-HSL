# Installationsguide für die Reinforcement Software

## Installation

Die Software basiert auf dem Repo des [NaoHTWK-GitHub](https://github.com/NaoHTWK/htwk-gym). Genauere Details befinden dort, die Installation wird hier weiter erklärt.

---

## 0. Software Voraussetzung

## 0.1 Hinweis:

_Die Installation ist angepasst an die neue Predator Flotte der R2K und deren Systemarchitektur. Installation auf anderen Geräten kann mögliche Fehler mit sich bringen._

Betriebssystem: Ubuntu 24.04.3

Die zu installierende Software innerhalb des Repos befindet sich unter rl_env/install-ressources.

## 0.2 Workspace

Erstelle einen Workspace Folder und gehe in diesen

```bash
mkdir Workspace
```

```bash
cd ~/Workspace
```

_Sollte der Name oder die Directory unterschiedlich sein, muss in den folgenden Schritten auf eigenständig auf die Bezeichnung geachtet werden_

Update vorher noch alle Pakete

```bash
sudo apt update
```

## 0.3 Git downloaden

Kontrolliere, ob git bereits installiert ist mit. Wenn ja, kann dieser Schritt übersprungen werden

```bash
git --version
```

Wenn nicht, installiere es mit dem Befehl und kontrolliere ob es installiert wurde

```bash
sudo apt install git
```

## 0.4 Python 3.8 installieren

Da wir mit einer veralteten Version arbeiten, müssen wir hier einige Extraschritte ausführen

```bash
sudo apt install software-properties-common
```

Nachdem die nötigen Tools gedownloaded sind, müssen wir das notwendige Repository downloaden

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
```

(Die Installation muss bestätigt werden)

Update nun nochmal

```bash
sudo apt update
```

Nun installiere Python 3.8

```bash
sudo apt install python3.8
```

Dazu noch die notwendigen Packages benötigt

```bash
sudo apt install python3.8-venv
```

```bash
sudo apt install libpython3.8
```

Kontrolliere, ob die Installation korrekt verlief

```bash
python3.8 --version
```

## 0.5 WandB

Sollte noch keinen Weights & Biases Account vorliegen, registriere dich [hier](https://wandb.ai/site/de/registry/)

---

## 1. HTWK Install

Als Erstes wird muss das Repo geklont werden

```bash
git clone https://github.com/NaoHTWK/htwk-gym.git
```

Danach muss eine virtuelle Umgebung mit Python 3.8 erstellt werden

```
cd ~/Workspace/htwk-gym
```

```bash
python3.8 -m venv venv_isaac
```

```
source venv_isaac/bin/activate
```

In dieser Umgebung wird dann PyTorch mit CUDA installiert

```bash
pip install --default-timeout=1000 torch==2.0.0 torchvision==0.15.0 torchaudio==2.0.0 --index-url https://download.pytorch.org/whl/cu118
```

Nun muss der NVIDIA [Isaac Gym](https://developer.nvidia.com/isaac-gym/download) heruntergeladen werden. Es wird die IsaacGym_Preview_4_Package.tar.gz benötigt, auch wenn unsere Ubuntu Version höher ist.

Gehe nun eine Directory zurück

```bash
cd -
```

Verschiebe nun die Datei in den aktuellen Ordner

```bash
mv ~/Downloads/IsaacGym_Preview_4_Package.tar.gz .
```

Nun extrahiere die Datei

```bash
tar -xzvf IsaacGym_Preview_4_Package.tar.gz
```

```bash
cd ~/Workspace/htwk-gym/isaacgym/python
```

```bash
pip install -e .
```

Die Python Abhängigkeiten werden jetzt installiert. Gehe dafür zurück in den richtigen Ordner

```bash
cd -
```

```bash
cd ~/Workspace/htwk-gym
```

```bash
pip install -r requirements.txt
```

Nach diesen Schritten kann die Simulation ausgeführt werden. Auf den neuen Laptops könnte jedoch ein Versionsproblem entstehen.

---

## 2. Versionskonflikte beheben

Downloade die [torch.whl](https://seafile.rlp.net/d/ebea374ecece4b55ae49/) Datei und lege sie in den Workspace Ordner. Installiere darauf die Datei

```bash
cd ~/Workspace
```

```bash
wget -O torch-2.4.0a0+gitee1b680-cp38-cp38-linux_x86_64.whl "https://seafile.rlp.net/seafhttp/files/57f0894d-bf3a-48e3-bffc-f57f2eaa08ea/torch-2.4.0a0%2Bgitee1b680-cp38-cp38-linux_x86_64.whl"~
```

```bash
pip install torch-2.4.0a0+gitee1b680-cp38-cp38-linux_x86_64.whl 
```

Update nun pip und räume Torch-Stände auf

```bash
pip install --upgrade pip
```

```bash
pip uninstall torchvision torchaudio -y
```

Danach muss Numpy downgegraded werden

```bash
pip install "numpy<1.24"
```

Als letztes muss noch die Vulcan Konfiguration neu gesetzt werden

```bash
cd ~/Workspace/htwk-gym
```

```bash
echo 'export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/nvidia_icd.json' >> venv_isaac/bin/activate
```

Als letztes muss noch folgender Befehl ausgeführt werden

```bash
sed -i 's/@torch.jit.script/# @torch.jit.script/g' ~/Workspace/isaacgym/python/isaacgym/torch_utils.py
```

---

## 3. WandB Login

Um sich mit einem bestehenden [Weights & Biases](https://wandb.ai/site/) einzuloggen, muss folgendes ausgeführt werden:

```bash
wandb login
```

(Sollte die Funktion nicht erwünscht sein, so muss im späteren Verlauf die .yaml Datei so geändert werden, dass die WandB Integration auf "false" gesetzt wird)

---

## 4. R2K Ressourcen Install

**WICHTIG:** Gehe im Repository zu [rl_env/install-ressources](https://gitlab.rlp.net/wisi1001/kickers-2025/-/tree/main/rl_env/install-ressources) und downloade die jeweiligen Dateien einzeln. Nicht den ganzen Ordner.

### 4.1 ParameterWalk.yaml

Gehe in den richtigen Dateinpfad.

```bash
cd ~/Workspace/htwk-gym/envs/K1
```

Danach ersetzen wir die Datei. Dafür müssen wir erst die alte ParameterWalk.yaml Datei löschen und durch eine leicht andersnamige Datei ersetzen

```bash
rm Parameter_Walk.yaml
```

```bash
mv ~/Downloads/ParameterWalk.yaml .
```

### 4.2 Sweep-Setup

Gehe zurück in den Hauptordner

```bash
cd ~/Workspace/htwk-gym
```

Hier ersetzen wir die train.py und fügen die sweep.yaml hinzu

```bash
mv ~/Downloads/train.py .
```

```bash
mv ~/Downloads/sweep.yaml .
```

### 4.3 Navigation-Setup

Verschiebe die Dateien in den Hauptordner

```bash
mv ~/Downloads/navigation_config.yaml .
```

```bash
mv ~/Downloads/controller_navigation.py .
```

**Achtung**: Dieses Programm braucht log Dateien um zu funktionieren. Passe dazu den Path in den Variablen an. Im Repository befindet sich ein aktuelles Model, so wird es richtig installiert:

## 5. Logs installieren

Downloade 2026-01-19-21-05-28.zip aus der [rl_env/logs](https://gitlab.rlp.net/wisi1001/kickers-2025/-/tree/main/rl_env/logs) Directory.

Gehe nun in den Logs Ordner

```bash
cd ~/Workspace/htwk-gym/logs/K1/K1/ParameterWalk
```

Sollten diese Ordner nocht nicht existieren, führe folgenden Befehl aus

```bahs
mkdir -p ~/Workspace/htwk-gym/logs/K1/K1/ParameterWalk
```

Gehe nun in den Ordner

Nun entpacke die .zip Datei aus dem Downloads Folder

```bash
unzip ~/Downloads/2026-01-19-21-05-28.zip 
```

---

Damit ist die Installation durch!

Zum Testen starte erstmal das Terminal neu

Dann gehe in den htwk-Ordner und öffne das Terminal. Aktiviere die venv

```bash
source venv_isaac/bin/activate
```

Und führe nun die play.py aus

```bash
python play.py --task=K1/ParameterWalk --checkpoint=-1 --num_envs=1
```

**Hinweis:** _Am Anfang kann das Rendern des Viewers einige Zeit dauern, da die Shader erst neu kompiliert werden müssen. Sei geduldig, solange keine Fehlermeldungen kommen, ist alles in Ordnung. Ignoriere einfach das Fenster, welches Anbietet, die Anwendung zu killen). Ist der Viewer innerhalb einer halben Stunde nicht geladen, ist etwas schief gelaufen._

Wenn du mehr über das Projekt finden möchtest, schaue dir den [Projektbericht](https://gitlab.rlp.net/wisi1001/kickers-2025/-/wikis/Projekt-HTWK-Gym) an. Dort findest du auch eine Übersicht über die einzelnen Befehle: [Befehlsdoku](https://gitlab.rlp.net/wisi1001/kickers-2025/-/wikis/Projekt-HTWK-Gym#4-anwendung)