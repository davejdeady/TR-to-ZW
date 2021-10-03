import datetime as dt
import logging
import os
import zipfile
from collections.abc import Iterable

from ..Model.TrainerRoad import TrainerRoad
from ..Model.Workout import Workout
from ..Utils.Str import *


def gen_zip_from_path(dir_to_archive, archive_filename):
    ziph = zipfile.ZipFile(archive_filename, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(dir_to_archive):
        for file in files:
            if file != archive_filename:
                ziph.write(os.path.join(root, file))
    ziph.close()


def create_plan_dictionary(response: Iterable) -> dict:
    saved_workouts = {}
    if bool(response):
        for workout in response:
            workout_info = workout.get(WORKOUT)
            if bool(workout_info):
                workout_details = workout_info.get(DETAILS)
                workout_id = workout_details.get(ID)
                workout_interval = workout_info.get(INTERVAL)

                if bool(workout_id):
                    workout_id = int(workout_id)
                    saved_workouts[workout_id] = {
                        DETAILS: workout_details,
                        INTERVAL: workout_interval,

                    }
    return saved_workouts


class Zwift:
    def __init__(self, username: str, password: str, output_folder: str):
        self.trainer = TrainerRoad(username=username, password=password)
        self.trainer.connect()
        self.workout_manager = Workout()
        self.output_path = output_folder

        try:
            os.makedirs(self.output_path)
            logging.info(f"Folder {self.output_path} does not exist creating path")
        except FileExistsError:
            pass

    async def export_training_plan(self, include_date: bool, start_date: str = "12-25-2020",
                                   end_date: str = "09-25-2023", compress=True):
        calendar = self.trainer.get_training_plans(start_date=start_date, end_date=end_date)
        workouts = list(set(calendar[ACTIVITY_ID]))
        response = await self.trainer.get_workouts_details(workouts=workouts)
        plan_dict = create_plan_dictionary(response)

        for date, workout_id in zip(calendar[DATE], calendar[ACTIVITY_ID]):
            workout = plan_dict.get(workout_id)
            if bool(workout):
                workout_details = workout.get(DETAILS)
                workout_interval = workout.get(INTERVAL)
                date: dt.datetime = date.strftime("%Y-%m-%d")
                workout_name = workout_details.get(WORKOUT_NAME)
                if include_date:
                    workout_name = f"{date} {workout_name}"
                    workout_details[WORKOUT_NAME] = workout_name

                if bool(workout_interval) and bool(workout_name):
                    try:
                        doc = self.workout_manager.convert_workout(interval=workout_interval,
                                                                   workout_details=workout_details)

                        doc_str = doc.toprettyxml(indent="\t")

                        filename = f"{workout_name}.zwo"
                        out_path = os.path.join(self.output_path, filename)
                        try:
                            with open(out_path, "w") as f:
                                f.write(doc_str)
                        except Exception as e:
                            logging.error(f"Error saving workout {filename}: {str(e)}")
                            pass
                    except RuntimeError:
                        logging.error(workout_name)
                else:
                    logging.error(workout_name)

        if compress:
            filename = os.path.join(self.output_path, "training_plan.zip")
            try:
                gen_zip_from_path(self.output_path, filename)
            except Exception as e:
                logging.error(f"Failed to save Zip File: {filename} + {e}")