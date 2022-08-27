from .tgs_api_models import *
from discord import Colour, Embed

def job_to_embed(job: TgsModel_JobResponse) -> Embed:
	state = job.state()
	if(state is JobState.Errored): color = Colour.red()
	if(state is JobState.Canceled): color = Colour.from_rgb(255, 255, 0)
	if(state is JobState.Stopped): color = Colour.green()
	if(state is JobState.Running): color = Colour.blue()

	emb = Embed(type="rich", title="Job #{} Information".format(job.Id), timestamp=datetime.utcnow(), color=color)
	emb.add_field(name="Job Information", value="Started:{}\nBy: {}\nDesc: {}".format(job.StartedAt, job.StartedBy.Name, job.Description), inline=False)
	if(state is not JobState.Running):
		emb.add_field(name="Job Completion Information", value="Stopped: {}\nCanceled: {}\nBy: {}".format(job.StoppedAt, job.Cancelled, "N/A" if job.CancelledBy is None else job.CancelledBy.Name), inline=False)
	if(state is JobState.Errored):
		emb.add_field(name="Error Information", value="Error #{}\n{}".format(job.ErrorCode, job.ExceptionDetails), inline=False)
	return emb
