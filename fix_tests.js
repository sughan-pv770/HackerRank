var r = db.tests.updateMany({}, { $set: { startTime: null, endTime: null } });
print('Updated:', r.modifiedCount, 'test(s) — now always active');
