"""""Half Circle Arm Extension on wall"""
import cv2
import mediapipe as mp
import numpy as np
import time
import threading
from Common import *
from exercise_state import stop_exercise_event
from exercise_ui import *

# Global variable to control the exercise loop
stop_exercise = False

class ExerciseApp:
    def __init__(self, ui):
        self.ui = ui
        self.root = self.ui.root
        # self.root.geometry("1400x800")
        self.root.attributes('-fullscreen', True)

        # Get screen width and height for scaling elements
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        print(f"{screen_height}*{screen_width}")
        video_width = int(screen_width * 0.85)
        video_height = int(screen_height * 0.85)
        x_position = (screen_width - video_width) // 2
        y_position = 20  # or adjust as needed
        self.video_label = Label(self.root)
        self.video_label.place(x=x_position, y=y_position, width=video_width, height=video_height)

        # self.start_button = Button(self.root, text="Start", command=self.start_exercise)
        # self.start_button.place(x=400, y=1020, width=120, height=50)
        #
        # self.stop_button = Button(self.root, text="Stop", command=self.stop_exercise)
        # self.stop_button.place(x=900, y=1020, width=120, height=50)
        #
        # self.quit_button = Button(self.root, text="Finish", command=self.quit_app)
        # self.quit_button.place(x=1400, y=1020, width=120, height=50)

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # resolution of the camera
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.2, min_tracking_confidence=0.2, model_complexity=0)

        self.stop_exercise_flag = False

    def perform_countdown_ui(self):
        start_time = time.time()
        countdown_sound.play()  # Play the countdown sound

        # Run the countdown loop for timer_duration seconds
        while time.time() - start_time < timer_duration:
            ret, frame = self.cap.read()
            if not ret:
                print("Camera frame not available.")
                return False

            # Calculate seconds remaining and draw the overlay on the frame
            seconds_remaining = int(timer_duration - (time.time() - start_time))
            display_countdown(frame, seconds_remaining)

            # Convert frame to format compatible with Tkinter
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img_tk = ImageTk.PhotoImage(image=img)

            # Update the video_label with the countdown frame
            self.video_label.config(image=img_tk)
            self.video_label.image = img_tk  # Avoid garbage collection

            self.root.update()
            time.sleep(0.03)  # Adjust delay as needed
        return True

    def start_exercise(self):
        # Perform the countdown using the video_label (no separate window)
        if self.perform_countdown_ui():
            self.stop_exercise_flag = False
            threading.Thread(target=self.run_exercise, daemon=True).start()
        else:
            print("Countdown was interrupted. Exercise not started.")


    def stop_exercise(self):
        self.stop_exercise_flag = True

    def quit_app(self):
        self.cap.release()
        cv2.destroyAllWindows()
        self.root.quit()



    def run_exercise(self):
        counter, reps, stage = 0, 0, None
        warning_message = None
        last_lower_sound_time = None
        timer_remaining = None
        is_timer_active = False
        last_beep_time = None
        last_good_job_time = None
        good_job_display = False
        sets = 0

        while self.cap.isOpened() and not self.stop_exercise_flag:
            ret, frame = self.cap.read()
            if not ret:
                break
            # frame = cv2.flip(frame, 1)
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


            warning_message = None
            try:
                if results.pose_landmarks:
                        landmarks = results.pose_landmarks.landmark

                        # Filter out landmarks with low visibility
                        visibility_threshold = 0.6
                        required_landmarks = {
                            'Left Shoulder' : self.mp_pose.PoseLandmark.LEFT_SHOULDER.value,
                            'Right Shoulder': self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
                            # mp_pose.PoseLandmark.LEFT_WRIST.value,
                            'Right Wrist' : self.mp_pose.PoseLandmark.RIGHT_WRIST.value,
                            # mp_pose.PoseLandmark.LEFT_ELBOW.value
                        }
                        missing_landmarks = []
                        for name, idx in required_landmarks.items():
                            visibility = landmarks[idx].visibility
                            if visibility < 0.5 or np.isnan(landmarks[idx].x) or np.isnan(landmarks[idx].y):
                                missing_landmarks.append(name)

                        if missing_landmarks:
                            warning_message = f"Adjust Position: {', '.join(missing_landmarks)} not detected!"
                            current_time = time.time()
                            if last_lower_sound_time is None or (current_time - last_lower_sound_time) >= 5:
                                visible_sound.play()
                                last_lower_sound_time = current_time

                        else:
                            rightshoulder = [landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                                             landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                            leftwrist = [landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                                         landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                            rightwrist = [landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                                          landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
                            leftshoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                                            landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                            leftelbow = [landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                                         landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                            # Calculate angles
                            angle = calculate_angle(leftwrist, rightshoulder, rightwrist)
                            frame_height, frame_width, _ = image.shape
                            left_arm_angle = calculate_angle(leftelbow, leftshoulder, rightshoulder)
                            cv2.putText(image, str(int(angle)),
                                        tuple(np.multiply(rightshoulder,  [frame_width, frame_height]).astype(int)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                            cv2.putText(image, str(int(left_arm_angle)),
                                        tuple(np.multiply(leftshoulder, [frame_width, frame_height]).astype(int)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (44, 42, 196), 2, cv2.LINE_AA)

                            # Exercise logic with state machine
                            # Ensure left leg is raised
                            if left_arm_angle > 160:
                                if angle > 160 and stage != 'start':
                                    stage = 'start'
                                    warning_message = 'Good form! Keep it up!'
                                    good_job_display = True
                                    goodjob_sound.play()

                                elif angle < 70 and stage == "start":
                                    stage = "down"
                                    counter += 1
                                    beep_sound.play()
                                    warning_message = "Complete Circle Down"
                                    feedback_locked = True

                                    # Every 5 counts, increase reps
                                    if counter >=5:
                                        reps += 1
                                        counter = 0
                                        success_sound.play()
                                        time.sleep(0.2)
                                        good_job_display = True
                                        goodjob_sound.play()
                                        last_good_job_time = time.time()

                                elif angle > 150 and stage == "down":
                                    stage = "start"  # Reset to allow another repetition

                                elif angle < 40 or angle > 177:
                                    feedback_locked = False  # Ensures bad form warnings only when necessary

                                else:
                                    warning_message = "Pose not detected. Make sure full body is visible."
                                    current_time = time.time()
                                    if last_lower_sound_time is None or (current_time - last_lower_sound_time) >= 5:
                                        visible_sound.play()
                                        last_lower_sound_time = current_time
            except Exception as e:
                warning_message = "Pose not detected. Make sure full body is visible."
                print("Error:", e)
                current_time = time.time()
                if last_lower_sound_time is None or (current_time - last_lower_sound_time) >= 5:
                    visible_sound.play()
                    last_lower_sound_time = current_time

            if good_job_display and last_good_job_time:
                if time.time() - last_good_job_time <= 5:
                    warning_message = "Good Job! Keep Going"
                else:
                    good_job_display = False

            # Draw pose landmarks on the image
            self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS,
                                           self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2,
                                                                       circle_radius=2),
                                           self.mp_drawing.DrawingSpec(
                                               color=(44, 42, 196) if (stage in ['too_high', 'too_low']) else (
                                                   67, 196, 42),
                                               thickness=2, circle_radius=2)
                                           )

            image = create_feedback_overlay(image, warning_message=warning_message, counter=counter, reps=sets)
            # cv2.imshow('Arm Extension', image)
            img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, (1280, 720))  # 1920, 1000
            # img = cv2.flip(img, 1)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            photo = tk.PhotoImage(data=cv2.imencode('.png', img)[1].tobytes())
            self.video_label.config(image=photo)
            self.video_label.image = photo
            self.root.update()

            if results.pose_landmarks:
                print("Pose detected!")
            else:
                print("No pose detected!")

            if self.stop_exercise_flag:
                break

        self.cap.release()
        cv2.destroyAllWindows()
        cv2.waitKey(1)

if __name__ == "__main__":
    root = tk.Tk()
    ui = ExerciseUI(root, title="Arm Extension")
    exercise = ExerciseApp(ui)

    ui.set_callbacks(exercise.start_exercise, exercise.stop_exercise)

    root.mainloop()
