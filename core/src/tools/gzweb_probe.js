// gzweb_probe.js — headless GZWeb verification probe (no browser needed).
// Verifies the gzbridge websocket data path: scene delivery + live pose streaming.
// Companion to setup_gzweb.sh (GUI annex N4, docs/gui_v67_discussion.md).
//
// Usage (inside the gazebo container, after setup_gzweb.sh + gzserver are up):
//   docker cp src/tools/gzweb_probe.js core_gazebo:/opt/gzweb/gzweb_probe.js
//   docker exec core_gazebo bash -c 'cd /opt/gzweb && node gzweb_probe.js 5'
//
// Argument: collection window in seconds (default 5).
// Exit 0 + "SCENE-MODELS(n): ..." with n > 0  => scene delivery OK.
// LIVE-POSE-UPDATES is non-empty only while entities move (gzweb filters
// static poses) — drive a bot via cmd_vel to exercise that path:
//   ros2 topic pub -r 20 /blue_1/cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.5}}'

const WebSocketClient = require('websocket').client;

const client = new WebSocketClient();
client.on('connectFailed', e => { console.error('WS-FAIL', e.toString()); process.exit(1); });
client.on('connect', conn => {
  console.log('WS-CONNECTED');
  const topics = new Set();
  let sceneModels = null;
  let sceneJson = null;
  const poses = {};

  conn.on('message', m => {
    if (m.type !== 'utf8') return;
    try {
      const j = JSON.parse(m.utf8Data);
      const topic = j.topic || '';
      topics.add(topic);
      if (topic.includes('scene') && j.msg && j.msg.model) {
        sceneModels = j.msg.model.map(x => x.name);
        sceneJson = j.msg;
      }
      if (topic.includes('pose') && j.msg && j.msg.name) {
        const p = j.msg.position;
        if (p) poses[j.msg.name] = [+p.x.toFixed(3), +p.y.toFixed(3)];
      }
    } catch (e) { /* partial frame */ }
  });

  // trigger scene_info exactly like the gz3d browser client does
  conn.sendUTF(JSON.stringify({ op: 'subscribe', topic: '~/scene' }));

  setTimeout(() => {
    console.log('TOPICS:', [...topics].sort().join(' | '));
    console.log('SCENE-MODELS(' + (sceneModels ? sceneModels.length : 0) + '):',
      sceneModels ? sceneModels.join(', ') : 'NONE');
    if (sceneJson && sceneJson.model) {
      const staticPoses = sceneJson.model
        .filter(x => x.pose && x.pose.position)
        .map(x => x.name + ':' + (+x.pose.position.x).toFixed(1) + ',' + (+x.pose.position.y).toFixed(1));
      console.log('SCENE-STATIC-POSES:', staticPoses.join(' '));
    }
    console.log('LIVE-POSE-UPDATES:', JSON.stringify(poses));
    conn.close();
    process.exit(sceneModels && sceneModels.length > 0 ? 0 : 2);
  }, parseInt(process.argv[2] || '5', 10) * 1000);
});
client.connect('ws://localhost:8080/');
