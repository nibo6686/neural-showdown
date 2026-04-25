import { EnvironmentManager } from '../src/env_manager';

async function main(): Promise<void> {
  const manager = new EnvironmentManager();
  let wins = 0;
  let losses = 0;
  let ties = 0;

  try {
    for (let battle = 0; battle < 1000; battle += 1) {
      const envId = manager.createEnv('gen9randombattle', [battle + 1, 2, 3, 4], {
        p1: { controller: 'random' },
        p2: { controller: 'random' },
      }).env_id;
      const result = await manager.resetEnv(envId);
      if (result.winner === 'p1') wins += 1;
      else if (result.winner === 'p2') losses += 1;
      else ties += 1;
      await manager.closeEnv(envId);
      if ((battle + 1) % 100 === 0) {
        console.log(`completed=${battle + 1} p1=${wins} p2=${losses} ties=${ties}`);
      }
    }
  } finally {
    await manager.closeAll();
  }

  console.log(JSON.stringify({ wins, losses, ties }));
}

void main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
